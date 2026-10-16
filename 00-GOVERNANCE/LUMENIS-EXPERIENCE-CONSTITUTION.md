# LUMENIS Experience Constitution — CURRENT

## 2026-10-11 当前体验纠偏：业务成果、贯穿式 AI、浏览器边界

CTH/BMP是业务领域；Shared内容制作提供独立入口。用户可直接新建文稿/提案、视频或播客，输入创作要求或导入获准素材并进行编辑，不先选商业主体/品牌、不先创建业务任务或来源简报。业务/研究成果进入制作属于可选续接路径；按用户选择带入资料与版本，不建立强制依赖。创作自己的Brief与项目由既有制作Owner管理，不能要求伪造业务上下文。

默认交互围绕用户的业务目标与可用成果。采集清洗、统计、数学方法选择、业务分析及报告组织在后端完成，前端展示已分析的结果，并提供范围/时间/业务约束、筛选比较、直接编辑、保存修订、引用追溯和恢复操作。不要把内部工程流程、论文计算器或 Agent 参数表变成普通用户的工作前提。

AI 在资料检索/理解、分析解释、研究、方案、创作与步骤辅助中上下文贯通；建议可检查、修改、拒绝，采用形成明确新版本。正常功能无模型仍可运行，AI 专属动作不可用应局部表达。不能把 AI 限成孤立聊天页，也不能让增强失败覆盖整个任务。

**采集资料的视觉呈现**：依已批准研究、当前任务和数据语义选择卡片、列表、表格或时间线，展示实际标题/正文片段、真实代表封面、作者、平台/原帖、原生时间与采集时间、真实指标与缺失原因。手绘彩绘只用于身份/对象图标及适合的局部页面元素；整体视觉不固定为2D或3D。来源类别同权；未取得字段显示“—”，真实零显示0。不得复制平台 Feed、伪造图片/热度，单封面不冒称媒体已读。原文、确定性派生、AI解释与人工判断分别可追溯。

**报告的视觉与内容层级**：结论与业务问题 → 依据/比较/图表 → 不确定性与适用范围 → 可执行建议及继续动作；来源与方法可展开。不能只交样本统计、原文拼接或等待用户配置算法的空报告。部分成果标明缺口，保留已有编辑，不用增量更新覆盖用户改稿。

通用电脑/OS控制从本产品撤回，§11与SYS-06只承担受控网页浏览、操作、接管、停止及任务返回。窗口调度只按直接PO指令和本地事实记录；规格更正不证明已构建或接受任何页面。

新增 REA 解析/原创适配成果按 Product Architecture 已确认用户工作蓝图第11节采用：视频和播客复用现有 Shared 媒体编辑基础，根据项目选择视频/音频模式，保留各自的预览、质量与成品验收；文稿、表格和演示成果通过现有资料/成果入口编辑、保存和导出，采用已验证的格式能力，不以 DOCX-only 阻挡其他获准成果。普通制作不新增“这是demo”勾选关卡，真正的素材权益、权限、版本和发布审批仍须执行。切换模式不丢轨道、附件或人工改动。采用方向已获PO确认；解析包不是完整厂商产品或已运行能力，实际接线与效果仍须验收。产品采用、执行计划审核、直接PO派工和实际验收分别记录。

> Status: **CANONICAL / SOLE EXPERIENCE DESIGN AUTHORITY**
> Internal version: **3.2**
> Effective: 2026-09-21
> Stable path: `00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md`

This file is the **only human-authored UI / UX / visual / interaction / motion / responsive / presentation design authority in the repository**.

No feature, domain, handoff, audit, research note, reference pack, screenshot pack, design-system document, component registry, motion specification, logo specification, page specification, AI prompt, historical artifact or code comment may create a competing presentation authority.

PDFs, taskbooks, reports, spreadsheets, screenshots, wireframes, Figma frames and
AI-generated visual proposals are non-authoritative working artifacts. They remain
`DESIGN_EXPLORATION` until their applicable screen/page decisions are deliberately
restated in this Constitution or in a reviewed detailed specification governed by it.
No artifact may promote itself or be copied directly into production UI.

Product/runtime/data truth still outranks presentation truth. This Constitution does not authorize changing backend facts, permissions, Evidence, canonical data or runtime semantics merely to make a screen easier to design.

## 0. Full-product scope

This Constitution governs every current and future user-visible or user-operable surface of 序境 / LUMENIS:

- account, authentication, onboarding and access states;
- global shell, navigation, Subject Context, Domain Lens, search, command and context switching;
- CTH / 序境·商业运营;
- BMP / 序境·品牌市场, including KOS / KOL / KOC / UGC workflows;
- Shared Capability, including Content & Creation, Evidence, Research, Evaluation and Learning;
- SYSTEM, including Collector, Runtime, Scheduler, AI Gateway, Database, Security, Permission, Settings, Recovery and Observability;
- AI / Agent workspaces and artifact flows;
- internal browser and evidence-acquisition surfaces;
- reports, exports, notifications, calendars and task surfaces;
- data visualization, tables, forms, editors, logs, status, empty/error/offline/blocked/loading states;
- Public Website, Web Workspace, Desktop App, tablet and Mobile Companion;
- Chinese / English / Korean presentation;
- brand identity in product UI, logo usage and launch/re-entry motion;
- any future surface added to this product.

Feature contracts may define **objects, fields, states, permissions, workflows and truth semantics**. They may not define a separate visual language or page-composition authority.

Historical browser presentation material was removed from `main`. Its templates/static implementations remain forbidden. The approved Public Website and Flutter Web Workspace are new surfaces under this same Constitution; retained contracts under `contracts/experience/` do not grant a second Experience design authority.

Historical design material is recoverable from Git history and user attachment
inventories. User-supplied references and requirements must be studied and mapped;
do not revive superseded design authorities or retired renderers. Keep bulky
reference media outside the source tree, with exact provenance and coverage
receipts in the existing research/evidence paths.

## 1. Authority order

For user-visible Experience work:

```text
Current verified Production Source / Runtime / Data / Permission / Evidence truth
> Production Acceptance and current product governance
> THIS CONSTITUTION
> current product/workflow contracts that define facts and states only
> implementation code / tokens / assets
> external research used temporarily during a task
```

There is no second design authority.

If code comments, old screenshots, component implementation or historical behavior conflict with this Constitution, they are implementation debt, not precedent.

## 2. Product identity

**LUMENIS is a Living Intelligence Space.**

It is not:

- a generic SaaS dashboard;
- an admin template;
- a BI dashboard;
- a CRM skin;
- a card-grid product;
- a Bento dashboard;
- an Apple clone;
- a Linear clone;
- a Notion clone;
- a copy of ChatGPT visual identity or proprietary assets; settings-section information structure may be studied and adapted with original LUMENIS presentation;
- a Korean-brand website clone;
- a generic AI-gradient interface.

External products may be studied for interaction principles, accessibility, motion, hierarchy or engineering technique. They are never the target appearance.

A user should be able to hide the logo and still recognize LUMENIS from its information grammar, Evidence trace, realm behavior, state transitions and workflow structure.

## 3. Philosophy translated into interaction

Brand philosophy: **芥子纳须弥**.

Experience interpretation:

> A small, real and verifiable point can reveal a larger structure; every larger conclusion must still be able to return to the original evidence.

Canonical business chain:

```text
Source → Evidence → Event → Case → Insight → Decision → Action
→ Outcome → Evaluation → Learning Asset
```

Canonical user question order:

```text
What changed?
→ Why does it matter?
→ What proves it?
→ What can I do?
→ What happened after the action?
```

Primary interaction verbs:

```text
Observe · Trace · Open · Compare · Shift · Decide · Act · Evaluate · Return
```

**Trace / Return** is a product signature. Important conclusions expose a natural route back to Evidence.

Metrics support understanding. Metrics are not automatically the page.

## 4. Native spatial grammar

LUMENIS uses:

- **Point**: one real object, fact, signal or Evidence item;
- **Axis**: time, causality, sequence or stable contextual relationship;
- **Trace**: the path from conclusion back to source truth;
- **Field**: an active working context, not a decorative container;
- **Strata**: layers of context, analysis, Evidence and action;
- **Boundary**: a semantic separation such as permission, source, state or workflow stage.

A rectangle is not automatically a Card. Border, radius, shadow and blur must express a real boundary or spatial role.

Default layout behavior must never be “put every object in a rounded rectangle”.

Whitespace is structural. Density is allowed when a task needs it, but density comes from relationships and information, not tile multiplication.

## 5. Typography

Semantic roles:

- modern UI sans: primary interface, controls, body and navigation;
- editorial serif: selective insight, narrative conclusion or interpretive emphasis;
- monospace: Evidence IDs, runtime identifiers, timestamps, traces and technical state;
- custom/handwritten wordmark: brand asset only, never ordinary UI copy.

Hierarchy comes from meaning, scale, rhythm and placement before decoration.

Web glyph fallback — 2026-09-28: keep the bundled SC/KR interface fonts and native
platform fallback. A licensed, version-pinned local emoji font may follow SC/KR
on Web to preserve user-authored Unicode without waiting for external font
services. This is missing-glyph recovery, not brand typography or decorative
emoji. Verify representative sequences, exact text return and package-size impact;
do not claim universal Unicode or native-device coverage from Web evidence.

## 6. Color, light and material

### Product Owner correction — four-surface creative Experience, 2026-10-03

This later direction supersedes assistant-authored storyboard-only, reduced-
interaction and limited-reference interpretations. Public Website, Web Workspace,
Desktop App and Mobile Companion all require upgraded creative UI/UX and AIGC
visual/interaction quality. Recompose for device and actual task; do not exclude
a surface as merely a wrapper or use mobile limitations to erase a requirement.
Preserve approved product/runtime roles and real capability handoff where needed.

The supplied painted-portrait reference supports original colored icons and
selected page illustrations where suitable; it does not define the product-wide
visual direction. Overall composition, spatial depth, layout, motion and
interaction follow the user's approved research, actual task and screen contract;
the product is not restricted to 2D or prescribed as all-3D. The reference
person is not a fixed character; characters follow the user's description/script.
Keep factual text, controls and semantic states readable.

Rich color is permitted. Use deliberate palette hierarchy, meaningful contrast,
controlled saturation/area and consistent semantic roles; do not impose arbitrary
monochrome, low-color or one-accent rules. Avoid indiscriminate color and
competing focal points. Evaluate actual composition rather than equating
creative richness with visual noise.

Interaction richness is required where it improves the work: direct manipulation,
selection/comparison, spatial or layered exploration, preview, transformation,
editing, source Trace and exact Return. Do not equate clarity, restraint or
accessibility with removing controls, motion, AIGC or creative interaction. Provide
keyboard/touch equivalents, interruptible transitions and user/system reduced-
motion support without deleting the underlying capability or making all default
experiences static. Different tasks need different compositions.

For Web Workspace, Desktop App and Mobile Companion, the scroll requirement
is no unnecessary page-level up/down scrolling. The Public Website is exempt
from this operational-layout restriction. Fit primary work and essential controls to the viewport;
use task-appropriate panes, zoom, timeline/canvas, reversible layers and explicit
navigation. Long documents, data or accessibility enlargement may need scrolling;
justify the region, preserve position/context and retain all information. Avoid
unnecessary nested scroll and elongated template pages; never clip content merely
to make a screenshot fit.

The latest explicit F instruction limits current frontend study to the two new
recordings, the earlier five supplied to F, existing analysis, OpenAI official
material and current product rules/requirements/architecture. Further exhaustive
analysis of other historical videos is no longer a frontend prerequisite. Retain
their originals and valid analysis as archives; the historical12 editing exercises
remain a distinct C4 corpus, not the seven frontend references. F and cooperating
owners retain their responsibilities; execution/pause state comes only from
AGENTS.md. The later Website-only 319b input
is covered by section 38. Record actual file/hash, frame count/PTS, visual transition, trigger,
state, task intent, four-surface adaptation and implementation/acceptance mapping.
Exact duplicate frames may share a read with a complete frame map; sparse
thumbnails or decoding alone never prove a full visual study. Reuse already valid
frame analysis without inventing coverage or repeating it.


### Product Owner direction — 2026-09-24 frontend reconstruction

The Product Owner explicitly rejected the previous visual proposal and requested
reconstruction around real business jobs, using the supplied desktop production
desk and focused mobile references. The historical 44-screen inventory is a
capability preservation checklist, **not a required page count or navigation
structure**. Merge entries, disclosures and stages where a continuous user task
benefits; keep existing deep links compatible and preserve every canonical owner,
data state, Permission boundary and backend contract.

The approved presentation direction is warm light workspaces, fine dividers,
compact project/task navigation, central working content and contextual tools.
Creation uses a script/editor/inspector composition; mobile uses one focused task
with secondary tools in reversible disclosures. Soft optical color and shallow
material depth may accent intent and creation entry points. Hover, press, drawer
and selection transitions must stay short and respect reduced motion. Business
records remain opaque, legible and stable. External screenshots authorize visual
adaptation through this direction; they do not establish source-code licensing,
business data, a new feature owner, or successful backend execution.

Frontend composition and reversible local editing may progress alongside backend
work. An unavailable backend must remain visibly unavailable, with no invented
audio, chart, result, save, publish or permission success. Existing screen
specifications retain their binding/effect restrictions while their composition
is revised under this Product Owner direction. Actual frontend operation and
business E2E acceptance are recorded separately.

The same Product Owner's subsequent direction adds device-local appearance:
frosted/translucent background, replaceable user wallpaper, desktop-system blur
where the platform supports it, pure white, pure black and custom solid color.
SYS-05 owns these device preferences; the existing Theme owner supplies contrast
roles to every workflow. A preference change must preserve drafts, selection,
route and scroll state. Images stay local and must never become Evidence or be
uploaded as a side effect. Storage or native-material failures remain explicit.
Web cannot reveal the operating-system desktop behind the browser; offer a
chosen wallpaper and in-page frosting there. Unsupported system effects must
not be represented as applied.

The two additional supplied videos are interaction references: orbital and
depth-based browsing, focused object/detail transitions, immersive backdrops,
transparent contextual tools and reversible drawers. Map each to an actual
user task and accessible controls; do not impose a repeated gallery or animated
card template on editing, data, decisions or settings. The reference inventory
records which moments were inspected and what is implemented versus pending.

The subsequent GPT/Codex appearance recording adds a typography requirement:
use a restrained hierarchy, comfortable body leading, readable secondary text
and aligned settings rows. SYS-05 offers a device-local base text size (14 px by
default, adjustable from 13 to 18) with a clearly labelled typography preview.
Apply the preference through the existing Theme/MediaQuery path, preserving
platform accessibility scaling, active route and drafts. Operational headings
must not use promotional hero sizing. Product copy uses the same bundled CJK
font families across workflows; weight, size and spacing express hierarchy.
Do not introduce a second theme owner or copy the reference application's
unrelated settings, code-diff viewer or account capabilities.

Color follows information.

Use neutral fields for truth-bearing content. Semantic colors communicate real state: success, warning, risk, blocked, stale, offline, selected or active.

A restrained luminous accent may identify active context, primary action, selected Evidence or current task. It must not become a decorative blue-purple AI wash.

Material roles:

- **Truth Surface**: Evidence, reports, long text, tables, forms, runtime facts. Stable and predominantly opaque.
- **Structure Surface**: context, toolbar, selector, filter, rail, drawer, popover. Subtle separation and shallow depth.
- **Optical Surface**: small, selective, optional interaction emphasis.

Fallback:

```text
OPTICAL → SOFT DEPTH → OPAQUE
```

No business function depends on blur, WebGL, GPU effects or glass. Glass is never the product theme.

## 7. Composition: reusable primitives, semantic screens

Reuse typography, spacing, icons, Evidence rendering, controls, input behavior, table mechanics, state semantics, accessibility, motion tokens and material roles.

Do **not** reuse a page skeleton merely because reuse is convenient.

Forbidden default ontology:

```text
Header → 4 KPI cards → chart → cards → table
```

Generic implementation sections such as `kpis`, `cards`, `split`, `chart` and `table` may remain during migration, but they are not a design language and may not dictate unrelated workflows.

Workflow-specific composition is expected when the user problem requires it.

## 8. Realm dialects

The realms share one grammar but must not be the same page with different labels or accent colors.

### CTH / Commerce Operations

Spatial idea: **time, event, place and operational change**.

```text
now_stream · event_flow · evidence_trace · case_evolution
decision_path · outcome_loop
```

CTH should feel temporal and causal.

### BMP / Brand & Market

Spatial idea: **network, brand, creator, content and propagation**.

```text
market_network · creator_constellation · content_cluster
market_movement · evidence_trace · relationship_path
```

BMP reveals relationships and movement, not another KPI overview.

KOS/KOL/KOC/UGC contracts define identity, ownership, states and fields. Their presentation still follows this Constitution.

### Shared Capability

Spatial idea: **transformation from brief/Evidence into artifact and learning**.

```text
creation_flow · brief_to_artifact · artifact_flow
evaluation_loop · learning_trace · research_path
```

Shared behaves like a creation/research workspace, not a reporting dashboard.

### SYSTEM

Spatial idea: **infrastructure truth made understandable**.

```text
runtime_topology · health_trace · collector_flow
permission_boundary · recovery_path · dependency_map
```

SYSTEM may be dense and technical. It exposes machine relationships rather than imitating an admin console.

## 9. Account, authentication and global context

The optional LUMENIS product account, login, recovery and settings are in the current engineering closure. The App opens without a global product-account wall; a protected operation may still show a local, truthful Permission boundary enforced by Product Core. Media-platform Cookie/session/browser authorization is a separate SYSTEM connector state and must not become a LUMENIS login flow.

When post-beta authentication/access surfaces are implemented, they are calm, direct and explicit about identity, permission, blocked state and recovery. They are not marketing landing pages.

Global Subject Context:

```text
GLOBAL_ALL → optional Subject / BrandFocus → Domain Lens → Scope / Permission
→ Function / Metric → ViewModel → Experience / Report / Export
```

CTH and BMP may interpret the Subject differently but must not create competing subject-context systems.

Navigation follows the current product/domain ownership in `LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md`, then the owning module and page. A route's existence alone does not make a destination top-level; keep utility workflows within their owning domain/module or the deliberate SYSTEM context. Navigation reveals current context and the next meaningful move rather than listing backend routes. No fixed rail/dock/sidebar shape is sacred.

## 10. AI / Agent experience

AI is **artifact-first**, not chat-first.

```text
Intent → Task → Runtime → Evidence → Artifact
→ Decision → Action → Evaluation
```

AI Home answers what can be understood or created.
AI Working answers what task is running, with what Evidence/state.
AI Result answers what artifact exists, what supports it and what can happen next.

Conversation history may exist, but chat bubbles do not dominate every task.

No fake thinking, fake progress, fake tool usage, fake confidence or fake success.

## 11. Internal browser / acquisition

### 2026-10-11 approved in-product browser and task continuity

The product provides a controlled browser within the originating business task.
The latest direct PO removes general computer/OS and installed-application
control from delivery; the browser remains. Source/import/export/media operations
inside LUMENIS remain required. Preserve old OS/Agent Zero source and evidence as
history, not a future acceptance debt or a completed capability.

Manual browsing and authorized page actions work without a model. AI may assist
web understanding and steps through the same task, actor, scope, session and
Permission boundary. Page execution, secure action/state transport and the visible
workspace viewport are separate responsibilities of existing owners. A static
image, external popup or failed iframe does not satisfy an interactive browser.
Website remains explanation/entry; Workspace, Desktop and Mobile implement their
approved operational roles in parallel and require separate actual acceptance.

Mobile: return/close and task identity at the top, safe destination and real page
viewport in the center, visible takeover/stop/current action, and a compact live
or historical-event strip below. Keyboard, touch, landscape, safe areas and
necessary page scrolling must work; historical frames are explicitly distinguished
from a fresh live session. Closing the view, stopping the task and ending a session
are different actions. Preserve draft, focus, selected source and return location.

Desktop and Web Workspace: keep the actual controlled page inside LUMENIS, with
task/operation context beside it when space permits. The product-owned browser
session may run on an authorized local/remote worker; do not promise arbitrary
third-party iframe embedding, control of the user's installed browser from a web
page, or silent access to local devices. Browser CSP/frame restrictions remain
enforced; never strip them through a proxy. A native WebView is optional only if
it demonstrably reuses the same owner/session/security contract and is justified.

Open externally is user-selected and uses the existing safe SourceTarget launch
boundary. No silent popup/fallback. Internal unavailable/error states keep Return
and the explicit external option; choosing external does not accept the unfinished
internal capability. No cookie, login or session state is copied to another app.
Navigation history controls and Return-to-task have different meanings. Tabs and
address editing are governed by actual existing supported actions, not inferred
from the video. The reference video shows browser task/viewport/takeover/status;
it does not prove the external option. General OS control was withdrawn on 2026-10-11.

Agent control and human takeover have an exclusive server-owned control lease.
Fresh target/frame/revision and coordinate transformation must be checked before
click/input/scroll; old actions cannot operate a new page. Stop/revoke/expiry must
prevent new actions and report in-flight uncertain effects honestly. Observation,
text entry, form submission and destructive/external writes are different effects
and pass existing Permission → Firewall → Effect Fence → execution → verification
and Evidence. Content is untrusted; no platform-challenge bypass, protected personal
profile access, credential projection, hidden arbitrary shell/CDP or account-wide
desktop access. Allow only task-authorized browser sites, page actions and explicit product file transfers.
No broad new account wall: remote/session security is implemented through existing
owners, preserving permitted local access.

The dated source audit initially found a read-only preview and incomplete browser
interaction/transport. Later bounded increments and current unaccepted browser
requirements are recorded in SYS-06 and the Real Delivery Overlay; this paragraph
does not freeze runtime status. General OS control was withdrawn on 2026-10-11
and is no longer a delivery gap. Existing F/C2/C6 responsibilities apply to the
retained browser path when dispatched; C1 reuses its authorized acquisition path.


The internal browser is an Evidence/acquisition workspace, not a decorative browser demo.

It makes source, identity/session boundary, collection state, provenance, risk and capture result understandable.

It must never imply that a source is authorized, captured, logged in or healthy unless runtime truth proves it.

Acquisition converges toward Evidence/Canonical truth, not a parallel browser-data silo.

### 11.1 Platform connector recovery

Media-platform authentication recovery is a SYSTEM connector operation, separate from the optional LUMENIS product-account login.

During approved R&D/internal-beta work, a Product-Owner-authorized owned platform identity may back a managed read-only connector. When its session expires or requires legitimate human interaction, the operational surfaces use one `LumenisPlatformRecoverySheet` contract rather than platform-specific app pages or raw browser windows:

```text
AUTH_REQUIRED
→ LUMENIS recovery sheet
→ QR scan when the platform provides QR

LOGIN_FORM_REQUIRED
→ LUMENIS recovery sheet
→ controlled internal-browser login surface

VERIFY / CAPTCHA
→ explicit human-verification state
→ never describe it as ordinary login

BLOCKED / IP_RISK / COOLDOWN
→ risk/cooldown state
→ do not show a QR as if login could solve it
```

When more than one platform needs attention, use one recovery sheet with a queue/list of affected platform sources and one active recovery task at a time. Do not stack platform-specific modal sheets or alerts. The sheet names the suspended source/task, keeps the origin visible enough to preserve context, and provides an obvious dismiss/defer path when the underlying task can safely continue with other sources.

The recovery sheet uses LUMENIS visual language while preserving the platform's actual QR/login content inside the controlled boundary. It never displays or logs Cookie values, tokens, profile paths, CDP endpoints or internal session identifiers. A button press, QR scan or login-form completion is not success by itself: the server-owned PlatformSession must re-read the real platform/runtime health before marking the connector recovered and resuming the exact pending task/checkpoint.

Modal accessibility follows the W3C APG dialog pattern and platform conventions: focus moves inside the sheet when it opens, Tab/Shift+Tab remain within the active sheet where applicable, Escape/system-dismiss closes only when cancellation is safe, and closing returns focus to the invoking control or the next logical workflow target. Asynchronous states such as waiting for QR scan, scanned, verifying, recovered or cooldown are announced as status updates without stealing keyboard/screen-reader focus. Reference standards: W3C APG Dialog (Modal), WCAG 2.1 Status Messages, and Apple HIG Modality.

Recovery returns to the originating CTH/BMP/Shared/SYSTEM task with scope, selection and work state preserved. Platform recovery must not create a second product account, silently expand source rights, start unrelated collection or perform social writes.

## 12. Evidence presentation

Evidence is first-class.

When available, expose source/provider, source identity/URL, capture time, relevant observable fact, freshness, lineage, confidence/rule basis and relationship to Event/Case/Insight/Decision.

Evidence must not be hidden behind generic “Details” when it supports an important conclusion.

Large conclusion → Trace → Evidence → Return without losing context.

## 13. Event / Case / Insight / Decision / Action

These are not equivalent CRUD records.

- **Event**: change over time, participants, propagation and lifecycle.
- **Case**: a working context accumulating Evidence, decisions and actions.
- **Insight**: a supported interpretation with explicit basis.
- **Decision**: a committed choice with owner/status where applicable.
- **Action**: an executable or proposed step with permission/effect boundary.
- **Outcome/Evaluation**: observed result and learning, not success decoration.

UI grammar reflects these semantic differences.

## 14. Data visualization

A visualization answers a question:

```text
Question → metric / relationship → visual form
→ interpretation → Evidence / lineage → possible action
```

Forbidden: decorative charts, rainbow palettes without meaning, “dashboard variety” donuts, duplicated numbers with no additional meaning, or values that cannot trace to canonical data.

Tables are tools for scanning/comparison/audit, not the default answer to every object.

## 15. Reports / exports

Reports are not dashboard screenshots.

Typical narrative:

```text
Conclusion → context → drivers → Evidence → comparison/trend
→ implication → action → evaluation state
```

Interactive UI, export and report derive from the same truth and Evidence lineage.

## 16. Content & Creation

Independent creation starts with the user's creative intent, handwritten content
or permitted media -> editable Draft/Project -> preview/review -> saved version
-> revise/reopen/recover and permitted export. It requires no CTH/BMP task,
Subject/BrandFocus or pre-existing research report. Source/Evidence is required
for factual claims and third-party material where applicable, not fabricated as
a prerequisite to an original draft. The following chain is the optional path
for continuing existing business/research context; publication and learning keep
their separate approvals and are not required to finish an ordinary local work.

```text
Brief → Context → Research/Evidence → Draft → Artifact
→ Review → Approval → Publish/Export boundary → Evaluation → Learning
```

The artifact is the center of work. Generated content is not published merely because a draft exists.

## 17. Forms / settings / configuration

Configuration makes scope, current value, consequence, validation and effect boundary explicit.

Avoid endless generic settings cards.

High-risk configuration shows permission, pending approval, irreversible effect and recovery where relevant.

## 18. State language

Never collapse:

```text
0 · NULL · UNKNOWN · NOT_AVAILABLE · NOT_COLLECTED · STALE
OFFLINE · ERROR · BLOCKED · PENDING · SCHEDULED · READY
RUNNING · COMPLETED
```

Missing data is not beautified into healthy state.

## 19. Motion

Motion explains relationship/state.

```text
ENTER · EXIT · TRACE · OPEN · SELECT · SHIFT · MORPH
EXPAND · COLLAPSE · DRILL · RETURN · PROGRESS
COMPLETE · WARNING · ERROR · RECOVER
```

Every meaningful animation has Before State → real Trigger → continuity principle → After State.

No state change usually means no animation.

Reduced-motion is mandatory. Brand launch/re-entry never blocks real readiness.

### Task-shaped interaction physics — direct PO addition, 2026-10-16

The PO requires weighty elasticity, magnetic attraction, fluid movement, throwing/inertia and other physics appropriate to the existing product task, with physical parameters that actually affect the motion. Preserve the existing motion vocabulary, time-based animations and user preferences; physics adds to or adapts the applicable direct-manipulation interaction, rather than replacing the product's motion wholesale. Use the existing frontend/component owners and this sole Experience authority, not a second physics engine, design system or rule owner.

For a spring, the relative mass, stiffness, damping, initial position/velocity and target must reach the real simulation/render consumer. An equivalent stable solution of `m*x'' + c*x' + k*(x-target)=0` is acceptable. Document normalized units, valid ranges and parameter version; relative mass is not a measured kilogram. Magnetic behavior uses real legal target geometry, attraction radius/strength or falloff, entry/release thresholds or hysteresis, and release velocity. Inertia uses measured release velocity, bounded speed, friction/deceleration, limits, restitution and position/velocity settling thresholds. Do not replace these controls with labels, fixed canned easing or a duration that makes parameter changes ineffective. Existing duration tokens continue to govern their time-based animations; physical trajectories and settling depend on the actual parameters and initial state.

Give reversible panels/objects a sense of weight, bounded elastic overshoot and stable landing; support continuous attraction, visible snap previews and intentional release near existing valid alignment targets. Throwing applies only where the existing task already permits dragging/browsing/editing, and must be catchable, interruptible, cancelable or reversible under that action's contract. Keep text/cursors and truth content stable. A visual snap or release cannot change business scope, permission, saved state, media timebase or playhead, and must never trigger deletion, publishing, payment or another external effect. Decorative button attraction must not move the hit region away from the pointer. Ordinary users should not need to enter physics constants to do business work.

Use elapsed time or a stable analytic solution, with bounded long-frame steps/substeps and lifecycle handling. Web CSS pixels, Flutter logical pixels and per-second velocities have explicit conversions; DPR affects raster density only. Position/velocity stay continuous when a target changes or the user reverses/regrabs, without queued stale animations. Resize, fonts, zoom/orientation, pointer cancellation, focus loss, navigation, disposal and background/resume invalidate stale targets/callbacks safely. Keep first-response feedback within its existing budget without delaying content, permission, persistence or readiness. Keyboard/touch/screen-reader equivalents and reduced-motion/off paths preserve the same real state and actions; reduced motion removes spatial throws/repeated rebounds and exposes the result immediately.

Acceptance requires actual operations plus time/position/velocity/target samples tied to the parameter and component version: from the same initial state, changing mass/stiffness/damping must measurably alter response, overshoot or settling; changing magnet radius/strength/release thresholds must alter capture/release; changing velocity/friction/restitution must alter inertia and rebound. Test reversal/regrab/cancel, limits, dropped frames and 30/60/120Hz where supported, with no frame-rate-dependent final state, NaN, runaway oscillation or leaked callbacks. Verify Website, Web Workspace, Windows/macOS and iOS independently for their applicable tasks, input, localization/200% text, reduced motion, performance and return. Parameters existing in source/config, a screenshot or one browser animation alone cannot pass. Missing connections or runtime evidence remain OPEN/NOT_VERIFIED; this rule starts no product implementation or window.


### Generated-result arrival — additive adoption, 2026-10-14

The PO's transitions-ui-generation addition preserves all previously approved motion, durations, visual direction and interaction. It adds a full one-shot generated-result presentation, never replaces or globally reduces existing motion. Users retain an independent choice for this effect (full / follow reduced-motion preference / off) and immediate skip; changing it must not change other motion preferences. Full presentation remains available. System/user reduced motion changes this effect only as selected.

Data pending uses the existing ordinary loading/skeleton state. Only a newly produced, permitted, version-identified useful result can arm the reveal; a queue acknowledgement, error, empty response, route entry, reopen, refresh or each list row cannot. First mount of old data is not a generation event. After the real result widget, fonts, layout and size-affecting assets are ready, measure its actual outline/text/controls and play the dot-field, construction/wireframe and reveal once for that result event. Result version changes during playback cancel the old effect. No invented layout geometry, Agent log, code-writing, token count, analysis or success appears in the overlay.

The effect is presentation, not computation, permission or persistence. Preserve real content, focus, accessibility tree and actions; skip/interaction can expose the result immediately. Resizing, scrolling, navigation, cancellation, failed readiness or reduced-motion changes must remove stale geometry and leave the real UI usable. Bound measurement and paint work; do not let a decorative failure prevent reading/saving/editing. Four-surface timing/performance and recovery require actual evidence. Website uses it only on a real permitted generated-result demonstration, never every hero/route; Flutter Web/native use actual render geometry, not a DOM overlay over its canvas.

Reference: [fixed source](https://github.com/Jakubantalik/transitions.dev/tree/9398105c07dafe877e43197b71c15a10a3b0e3f6/skills/transitions-ui-generation); the skill's custom Transitions.dev license permits free commercial product integration but bars repackaging the library as a competing animation collection. It is not wholly MIT/OSI-unrestricted. Record any adopted files/port and notices in the existing third-party register. This is an existing Experience rule and registered component adaptation, not a new visual authority or replacement design system.

## 20. Responsive recomposition

Validation widths:

```text
1920 / 1440 / 1280 / 1024 / 768 / 430 / 390 / 360
```

Responsive means recomposition, not desktop scaling.

Preserve semantic continuity while changing placement and interaction form.

No screen is accepted because it only works at one zoom or width.

## 21. Accessibility

Keyboard, focus visibility, semantic labels, contrast, touch target, screen-reader structure and reduced motion are part of design.

Hierarchy must survive without color alone.

## 22. Trilingual copy

```text
Machine ID → Semantic Copy Key → Display Value
```

Real Subject names, Brand names, Event titles, Evidence and business records remain data, not locale copy.

Chinese / English / Korean preserve meaning and hierarchy rather than identical string length.

The product commitment is three user-visible language versions (`zh-CN`, `en`,
`ko`) across the Public Website and every operational Web Workspace, Desktop
and Mobile workflow that a Round promises to deliver. A committed website
translation or a local App copy registry does not establish a released locale.
Each applicable screen specification and Round acceptance must name its three
locale paths, state/error/permission/accessibility copy, switching and restored
context, missing-key behavior and tested responsive layouts. If one promised
locale is absent or unusable, that screen/surface is not accepted; it is not
silently deferred or replaced by untranslated implementation text.

## 23. Brand identity

Product assets may live in implementation directories, but there is no independent logo/design specification outside this Constitution.

Identity should feel precise, restrained, spatial, evidence-led and contemporary without AI-template decoration.

Existing logo/icon assets are assets, not authorities. Future brand changes are decided here first, then implemented.

### Restrained identity and content space — 2026-09-28

The Product Owner asks for less spectacle, a replacement for the boxed single
character mark, and adaptation from creative industries. Sol presentation review:
`DESIGN_READY` for the following bounded shell changes. This does not accept a
complete screen, native surface, product or Round.

Express 芥子纳须弥 through a small point and open, nested contours, alongside the
plain product name when space permits. Per the PO rule in USER-ADDITIONS-20261004
(lines 62-66, "colour hand-drawn texture as shown"), the brand mark is a hand-drawn
colour mark (coloured pencil + watercolour, cream paper #F9EED9, outline #583830):
a jasmine in its real growth form with a snake, in named and unnamed versions.
The in-product shell mark and sizes up to 32px use its single-colour silhouette
(#583830, or the theme foreground in dark mode); it is unboxed,
static and subordinate to the user's content. It has an accessible product name;
it does not indicate connection, processing, confidence or data completeness.
Do not use an oversized sculpture, rotating orb, breathing logo or generic AI
gradient as the identity; the hand-drawn pigment colour of the brand mark is media, not a UI gradient, and does not spread to the shell. This is the in-product mark; package icons and the
public website remain separately reviewed surfaces.

At desktop and compact-workspace widths, keep a visible navigation trigger and
the current task/context; expose the existing domain/workflow hierarchy in a
reversible navigation layer rather than an always-present application catalogue.
All registered destinations and deep links remain available. Closing navigation
without choosing a destination restores the mounted task, draft, focus and scroll;
choosing a destination uses the existing route/context owner. Escape, explicit
close, keyboard traversal and touch must work. Avoid hover-only discovery,
invisible gesture-only navigation or new project/recent/search capabilities.
Mobile retains its focused task and existing navigation until a separate change
proves the same reachability; it is not a compressed desktop catalogue.

Creative-industry research, accessed 2026-09-28, principle-only:

- [Figma UI3 design review](https://www.figma.com/blog/our-approach-to-designing-ui3/)
  (2024-10-01, official maintained site, proprietary editorial material): ADAPT
  content priority and explicit minimized navigation. Its reported floating-panel
  reversal is a reason to test task speed and available space. Do not copy the
  layout, assets or add the Figma product model.
- [Are.na material attribution](https://help.are.na/docs/guides/handling-blocks-with-care)
  (current official guide, proprietary product/content): ADAPT context and source
  attribution as existing Trace/Return behavior. DEFER a general-purpose board or
  social collection workflow; no new owner, API or data store is authorized.
- Flutter 3.47.5 at `6a19cca56475dbfba1478ee68d7bd0c2ef891da1`, BSD-3-Clause,
  maintained upstream: reuse existing route, dialog, focus and paint primitives.
  No new runtime dependency, copied asset, external effect or account is needed.

The original F user message at session 01a0cf2d-6ece-7c90-8877-b58fc80a4480,
line13050, distinguishes AIGC/3D frontend presentation from a request to add an
AIGC-production feature. The current four-surface direction requires original
generated visuals, creative composition and rich interactive/motion presentation;
it is not limited to a static illustration. Do not infer a new generation module
from this frontend requirement. Separately approved AI/content-creation business
capabilities retain their own full owners and acceptance. Preserve existing
Permission, material/version and real-state bindings; no second AI owner is added.
The generated optical sculpture explored
on this date is `DESIGN_EXPLORATION / DEFER`, excluded from the production asset
bundle pending a restrained, task-specific review. Depth/motion must clarify a
real layer or selection, be interruptible, and become immediate in reduced motion.

### Order with a human scale; Reelfolio research — 2026-09-28

The Product Owner asks for order, precision and consistency balanced by humanity,
culture and brand awareness. Express 芥子纳须弥 through restrained framing and
progressive access to meaningful detail. Give real language, work and source
material room to breathe. Do not turn cultural identity into ornamental symbols
or equate warmth with a compulsory gradient, animation or invented personal data.

Official [Reelfolio editor](https://reelfolio.io/dashboard), accessed 2026-09-28:
Sol inspected its Riffle example, paused playback, and collapsed both Templates
and Settings. The resulting media area retained explicit reopening controls.
The live service has no inspected public source revision or reusable code/asset
license; treat it as proprietary reference material, not an OSS dependency.

- ADAPT clear content priority, explicit reversible secondary controls, and
  depth that identifies the currently selected object. Existing Shell navigation,
  AI-01 expanded draft/Return and SYS-05 preference preview own these principles.
- DEFER material-stack/spatial media exploration to a real, scoped content
  selection/preview task. SH-01's three creation paths, Permission, missing data
  and read-only limits remain intact; no generic carousel replaces them.
- REJECT autoplay loops, cursor trails, robot/liquid spectacle, copied layouts,
  templates/assets, or a new render API solely to reproduce the reference.
  Critical text, Evidence, metrics and actions remain flat, stable and readable.

Sol presentation decision: `DESIGN_READY` for removing AI-01's three decorative
background glows. Keep the current resolved canvas/wallpaper material, every
business and recovery state, typography, local draft and reversible focused
editor. This is a bounded simplification of the existing owner. It authorizes no
new page, effect, data meaning, brand asset or overall frontend acceptance.

### Task Home, collected-source presentation and Discover — 2026-10-03

2026-10-12 direct PO clarification: opening the operational workspace lands directly in the conversation/task home. ACC-03 reuses the existing AI-01 conversation, composer, draft, ViewModel and result owner; it does not add another chat service. Navigation opens the existing CTH, BMP, Shared research and independent proposal/video/podcast creation, controlled browser and SYSTEM destinations. These remain directly usable, with optional linkage and useful non-AI operations. Default scope is GLOBAL/ALL, with optional exact Subject/BrandFocus. Do not substitute a dashboard, marketing hero, introductory cards or a domain/model-selection prerequisite for this entry.

Study GPT and Grok Bot official operation guidance and permitted REA observations together for the existing conversation: understandable input and attachments, editable context/drafts, progressively useful replies, task-appropriate Intelligent UI, actual progress, stop, safe continuation, result/citation actions, history, save/revise/reopen and recovery. F owns original LUMENIS presentation and the existing ACC-03/AI-01 contracts; C2/C6 own actual task/action/result contracts; C3/C4/C5 remain business/output owners. Preserve input, selection and accepted partial results on navigation, reconnect and cancellation; resume from the server's committed result, not a blind repeat. A missing model disables only the genuine AI-exclusive action, not access to normal domain/research/creation tasks. Existing four-surface roles and acceptance remain; Public Website leads into the workspace and retains its own content role. Missing actual behavior stays honest and is repaired by its owner, not shown as fake chat or fake progress.

All collected platform lists, details, media, source results and recommendations use LUMENIS information hierarchy, interaction and visual language. Retain native facts, original logos/attribution, source URL, locators, times and metrics; source-platform visual chrome, copied XHS/Douyin feed/layout, endless swipe or forced autoplay are not the product interface. Avoid replacing them with one generic repeated card template. Detail/media reading is reversible and preserves task/context/scroll continuity and honest states.

### Platform-native SourceTarget / Open Original — Product Owner approved 2026-10-06

The approved source handoff is **LUMENIS SourceTarget v1**, subordinate to this Constitution and the existing Product Core, Permission and Evidence owners. Its canonical path is:

```text
platform-native observation
→ Source → Evidence → Canonical
→ CTH/BMP task-specific LUMENIS presentation
→ Trace → Open Original
→ in-product SYS-06 viewing (explicit external-browser option)
→ Return to exact task/context/filter/selection/scroll state
```

`contracts/experience/source-target-contract-v1.json` is the machine-readable binding contract. A usable target retains `source_platform`, nullable `source_url`, source/canonical/Evidence references, locator, publication/capture time, availability and a Return context. Missing, invalid, denied, unsupported, launch-rejected and launch-failed states remain distinct; a browser accepting a handoff does **not** prove the page loaded, remained available, authenticated or readable.

“查看原贴 / Open Original” is an explicit user-gesture, read-only opening of an allowlisted public HTTPS destination. The 2026-10-08 requirement makes the existing SYS-06 controlled in-product view the target default on operational surfaces; “Open externally” is a separate explicit choice. SourceTarget v1 currently binds the legacy external adapter only and does not satisfy that new default. F/C6 must migrate its mode selection and callers together without weakening URL, lineage or Return checks. It must never silently inspect or export local cookies/session state, log in, start or resume collection, capture Evidence, mutate Canonical Data, publish, message, purchase or perform any external write. Ordinary source opening and SYS-06 controlled navigation/capture are separate actions and separate acceptance paths.

Web Workspace, Desktop and Mobile recompose the same source truth for their task and form factor; they do not recreate the source platform UI. Public Website may explain the behavior but never exposes protected business rows or owns the source action. Return preserves the originating route, GLOBAL/FOCUS, Subject/BrandFocus, filters, selected object and scroll position. This approval defines the required result only; it is not implementation, live launch, device or user acceptance evidence.

The existing SH-01 research/creation workspace includes a bounded Discover view: task-relevant trends, observed hotspots and similar works, with explicit scope/platform/time filters, relevance explanation, source/citation and missing/partial states. A single-platform collection request remains available. The owned Gateway may analyze authorized product materials and suggest alternatives, reasons and original creative directions; static entry cards, source excerpts or Codex answers cannot pretend to be this analysis. Selected references enter existing Brief/creation owners with actual use authorization.

AI-01, ACC-03 and SH-01 specifications carry the detailed bounded design. A design-approved requirement or this rule is not implemented/live accepted. F keeps each screen's task-specific composition, responsive behavior, localization and accessibility; W6 binds the same real Core contracts across approved surfaces. No new screen ID, model owner, database, recommendation authority or design system is created.

### Functional glyphs and surface assets — 2026-10-03

M reviewed the complete original functional atlas at 16/18/20/24 logical-pixel
sizes and its exact semantic aliases. The bounded glyph language is
`DESIGN_READY`: a 24-unit grid, optically corrected open geometry, restrained
rounded strokes and familiar navigation/editing/transport meanings. Play,
pause and simple selection marks may use deliberate solid geometry. The
existing App visual/Theme owner supplies one implementation; no independent
icon system or design authority is introduced.

Use 14–16 logical pixels for inline metadata, 18 for editing toolbars, 20 for
navigation and 24 for deliberate transport emphasis. Glyph size is separate
from the accessible interaction area, ordinarily 44–48 pixels or greater.
Preserve IconTheme color/opacity/size, semantic labels and exclusions,
Directionality where applicable, focus, disabled/selected behavior and native
control semantics. A custom painter does not establish accessibility by itself.
Aliases may share a glyph only when they share meaning; newly encountered
symbols require explicit coverage rather than a silent generic substitution.
Actual state remains legible in text and must not be conveyed by a glyph alone.

The approved static point/open nested-contour product mark remains the common
identity for App, Website, favicon and native/package assets. Website header
and footer keep the unboxed mark and existing product text. Small favicon and
package variants may place the same optically corrected silhouette on an opaque
warm-neutral field, respecting the platform mask and safe zone. Preserve real
source brand logos/avatars and their provenance. Package variants must not
change signing identifiers or imply a business, connection or readiness state.

F produces the complete isolated glyph/asset candidate and exact format,
dimension, alpha and before/after hash inventory. W6 integrates frozen App
inputs, launch/package assets and existing entry defaults. Functional atlas
approval does not accept generated package artwork, a mounted interface or an
installed executable. Review representative real light/dark/wallpaper contexts,
large text and three locales; verify actual Website/Web/Desktop behavior and
each promised native/package surface separately. Missing device or installed
launcher evidence stays `LIVE_NOT_VERIFIED`.

## 24. Anti-template hard failures

Unless a current product requirement proves a narrow exception, fail review when:

- a Golden Page has a top-level generic `kpis` section;
- a Golden Page uses generic `cards` as its main composition;
- unrelated realms share the same top-level page signature;
- a home/overview opens with a four-column KPI wall;
- CTH can become BMP by changing only labels/data/accent;
- Event/Evidence/Case/Insight become equivalent CRUD objects;
- AI result defaults to chat bubbles instead of Artifact;
- glass becomes the global theme;
- another brand name is used as target style;
- CSS decoration changes but semantic hierarchy does not;
- many pages are declared complete because one generic schema renders them;
- a parallel design/handoff/reference document is committed.

## 25. Golden Pages

1. **AI-01**: `intent_space + evidence_trace + artifact_flow`
2. **CTH-01**: `now_stream + event_flow + evidence_trace`
3. **BMP-01**: `market_network + evidence_trace`
4. **SH-01**: `creation_flow + artifact_flow`
5. **SYS-01**: `runtime_topology + health_trace`

All five have distinct top-level semantic signatures before broad migration.

Remaining screens migrate by workflow family, not bulk skinning.

## 26. Codex / Agent execution

Before Experience implementation:

1. resolve current `origin/main`;
2. read root `AGENTS.md`;
3. read **this file**;
4. read retained `contracts/experience/` assets only as App binding contracts;
5. inspect current Source / ViewModel / State / Action / Permission / Evidence / Runtime owners;
6. state the user problem and semantic composition before editing CSS.

Implementation order:

```text
User problem → semantic objects/relationships → composition
→ shared primitives → realm behavior → real binding → states
→ responsive → motion/material → acceptance
```

Forbidden order:

```text
choose fashionable style → add cards → add glass → insert data → call it LUMENIS
```

For non-trivial work, the plan names active workflow, truth sources, semantic primitives, generic pattern being retired/avoided and acceptance checks.

## 27. Repository exclusivity

The current main tree must not restore superseded UI/UX/visual authorities,
retired templates or competing design systems. This is not a ban on studying
user-supplied videos/images, historical requests or research. Preserve their
exact references and adoption/coverage records; promote applicable requirements
through this Constitution and current detailed specifications. Bulky original
media remains in its protected material location rather than the Git source tree.

Those remain recoverable from Git history.

If research is needed:

```text
research externally → extract principle → decide
→ update THIS Constitution only if canonical → implement
```

Do not commit a second design bible.

Blocking checks:

```text
python scripts/audit_tools/verify_experience_authority_exclusive.py
python scripts/audit_tools/verify_experience_anti_template.py --strict
python scripts/audit_tools/verify_experience_screen_blueprints.py
```

## 28. Acceptance

Experience completion is not “page renders”.

```text
Semantic question → ViewModel truth → composition → Evidence trace
→ action → honest state/error → responsive recomposition
→ screenshot regression → ARIA/structure regression → runtime/E2E
```

New screenshot baselines come from **V3-compliant Golden Pages**, never inherited legacy baselines.

Snapshot regeneration is not acceptance by itself.

Anti-template thresholds are ratchet-only.

## 29. Current state

This sole authority does not claim current implementation is already compliant.

Current honest state:

```text
SOLE AUTHORITY ACTIVE
LEGACY DESIGN AUTHORITIES REMOVED FROM MAIN TREE
IMPLEMENTATION MIGRATION REQUIRED
```

Current production CSS/JS/assets may temporarily contain legacy implementation structure until migrated. They are implementation, not design precedent.

## 30. Canonical multi-surface architecture and feature ownership

The product is delivered through an SEO-capable Public Website plus one Flutter implementation for Web Workspace, Desktop App and Mobile Companion. All four surfaces share business semantics and contracts while adapting composition and input to browsers, native Windows/macOS and native iOS; they are built in parallel and accepted independently under their approved roles. Linux server/CI and browser availability are distinct from native delivery targets. Bind available real APIs/Core immediately; missing existing-owner behavior remains OPEN/UNBOUND while connected. The approved roles and capability boundary are recorded in `LUMENIS-MULTI-SURFACE-DECISION-CURRENT.md`; this Constitution remains the sole design authority. See the approved 2026-10-11 receipt `evidence/approvals/PO-20261011-WHOLE-PRODUCT-REUSE-EXPERIENCE.json`.

```text
Flutter composition root
├─ core        transport, typed contract decoding, auth/session, errors, cancellation
├─ account     optional product identity/sign-in/recovery/settings; never a global account wall
├─ cth         SubjectContext, commercial operations, events, cases, decisions/actions
├─ bmp         BrandFocus, market signals, creators, campaigns, propagation/evaluation
├─ shared      Evidence, research, creation, evaluation, learning, reports/export
├─ system      permission-gated runtime, collection, security, settings, recovery
└─ navigation  routes, deep links, restored work context
```

The folder map is an implementation boundary, not a second truth owner. Surface state may hold presentation state and a restorable navigation context; it must not become Canonical Data, Evidence, Metric, Permission, Runtime or business-state truth. The Public Website may own public content presentation and acquisition forms only. Agent Groups remain the cross-product execution/collaboration layer and are not a product domain.

Before implementing each screen or action, complete this binding:

```text
ScreenId / ActionId
→ current source and canonical owner
→ API request/response and typed ViewModel
→ actor, target, scope and Permission decision
→ Evidence lineage and write/effect boundary
→ loading / empty / UNKNOWN / stale / blocked / failure / success state
→ action result, evaluation and trace-back behavior
→ widget / integration / runtime acceptance
```

Use `contracts/experience/` as a binding contract, never as proof that an endpoint or action already exists. `UNKNOWN`, `NOT_AVAILABLE`, `NOT_COLLECTED`, `STALE`, `BLOCKED` and `ERROR` must stay distinct. A fixture, optimistic UI state or AI answer cannot fill a backend gap or imply a successful production action.

### Domain invariants

- **CTH** starts from an authorized Subject. Selecting or changing a Subject changes working context and filters only; it never rewrites Evidence, Canonical Data, original ownership or confirmed outcomes.
- **BMP** starts from a Brand/Market focus. The selected brand is the primary focus while competitors, creators, content, consumers and market movement remain visible relationships. BMP is not a CTH subject page with different labels.
- **Shared Capability** preserves `originDomain`, source object and lineage when a capability is opened from CTH or BMP; it does not take over their business ownership.
- **SYSTEM** actions are effect- and permission-gated by the Core. Hiding or disabling a control on any surface is not authorization.

## 31. Cross-surface composition

Responsive acceptance uses the widths in §20 and verifies a semantic recomposition, not a scaled desktop screenshot. Public Website and Web Workspace are distinct products surfaces: the former explains/acquires, while the latter operates real workflows.

| Form factor | Composition contract |
| --- | --- |
| Public Website | SEO-readable product narrative, capability proof, truthful demo/case material, trial/contact/help and a clear workspace entry. Optional sign-in and account recovery have clear entries alongside direct workspace access; no account wall is imposed. It cannot resemble or execute the operational workspace. |
| Web Workspace | Browser-first primary operating surface with URL/deep-link semantics, keyboard/pointer access and responsive evidence/workflow composition. Desktop-only capability exposes a truthful handoff/state, never simulated success. |
| Wide desktop (≥1280 logical px) | Persistent product/domain navigation, a compact active-context bar, workflow-specific work surface, and an optional Evidence/inspector region. The inspector may resize but cannot obscure the primary task. |
| Compact desktop/tablet (768–1279 px) | Collapsible navigation rail, one primary work surface, and Evidence/inspector as a reversible panel. Keep keyboard navigation and selected context visible. |
| Mobile Companion / phone (≤767 px) | Notifications, events, AI results, approvals, task state, report reading and bounded quick action. Keep the authorized Subject or Brand focus visible and preserve source context on return. |

The breakpoints guide composition; measured content and platform window size determine the final layout. Desktop favors parallel comparison and precise pointer/keyboard work. Mobile favors a single active task, touch-sized actions and context that remains visible without consuming the work area. Platform-specific navigation must not create different business meaning.

Phone refinement reviewed by root on 2026-09-27, following the Product Owner's
request to remove the templated mobile composition and fix desktop details:
one compact header keeps the current page and authorized context visible; a
labelled page chooser reveals the existing workflow groups in a reversible
sheet instead of a second permanent horizontal navigation strip. The five
domain destinations remain directly reachable. Account, language and service
status stay available from the header's tools menu; appearance remains a direct
action. No route, context selection, permission or data meaning changes. The
existing screen host retains its State across width changes. AI-01 keeps a
single writing surface on phone; SYS-05 groups wallpaper selection, preview and
adjustment in that order. Their detailed specifications own the corresponding
presentation decisions. This is a presentation approval, not business, native
runtime, complete frontend or Round acceptance.

The Product Owner's 2026-09-27 phone recording adds a bounded abstract mapping:
retain the current work beneath a settings layer, group controls by task, and
keep return/close visible while content scrolls. Navigation/tools sheets have
a fixed title and explicit close action. Device appearance uses a phone sheet
with a visible originating page and a right-side inspector at wider widths;
both retain the same preference owner and unsent work. This mapping does not
import the reference application's accounts, subscription, memory, plugins or
OS settings, and is not authority to reproduce its feature set or layout.

## 32. LUMENIS interaction signature and motion contract

LUMENIS’s distinctive interface is the **Trace / Return** relationship expressed through its existing spatial grammar: Point → Axis → Trace → Field → Strata → Boundary. A conclusion can reveal its evidence lineage along the relevant time, relationship, creation or runtime axis; Return restores the exact prior focus, filters, selection and scroll position. This behavior is implemented in each domain’s own composition, not as a generic detail drawer repeated everywhere.

Every non-trivial motion/action specification records:

```text
user intent → trigger/input → before state → visible change
→ business/data/Evidence cause → cancel/reverse/return
→ keyboard and touch equivalent → reduced-motion equivalent
→ accessibility announcement → device/frame-budget acceptance
```

Motion may clarify causality, selection, progress, successful persistence, blocked effects or recovery. It must not delay readiness, hide a data change, imply an unrecorded write, intercept ordinary scrolling, or be required for meaning. Prefer direct manipulation with bounded, interruptible transitions. Test actual input and resulting state; a screenshot alone is not motion acceptance.

## 33. Inspiration and originality boundary

External creative work, including Korean product-app craft and `motion-web`, may inform general principles such as task clarity, progressive disclosure, crisp response, restrained transitions, accessibility and measurable interaction quality. Product semantics, information architecture, composition and visual identity remain LUMENIS-owned and are derived from real domain objects and workflows.

The named examples below are non-exhaustive. The user's historical and current
video/image requirements take priority over an assistant's narrow reference list;
extract and adapt their actual visual and interaction mechanisms, record the
frames studied and restate the chosen design here or in a governed specification.
The earlier examples are: Apple informs restraint, content priority, one clear primary action and an uncluttered search entry when an existing workflow is search-led; ChatGPT informs a single intent entry and progressive disclosure of existing complexity; TRAE informs visible **task → execution → result** feedback for existing workflows. These references do not authorize new Chat, Work, Project, recent-content, search, task-platform or account capabilities, and they do not replace any current business function or backend owner.

For Korean product-app craft, study public product-engineering documentation such as the [Toss Design System component guide](https://developers-apps-in-toss.toss.im/landing-page/landing-page-en/design/components) for consistency, clear component guidance and task-focused implementation. Its UI Kit terms restrict use of Toss materials to the Apps in Toss service, so LUMENIS does not adopt the UI Kit, components, assets or visual patterns. Extract only general, non-visual principles, then test those against LUMENIS workflows.

Do not copy another product's assets, source code, signature layout, visual identity, interaction sequence or implementation recipe. The supplied [motion-web repository](https://github.com/Zachary-1012/motion-web) is a fork of `feitangyuan/motion-web`; its [LICENSE](https://github.com/Zachary-1012/motion-web/blob/main/LICENSE) identifies CC BY-NC 4.0 and expressly restricts commercial integration of its Skill, prompts, cases and derived workflows. No code, case, asset, parameter set or derivative workflow from it is admitted into this commercial product. Inspiration is not a runtime dependency or a competing design authority. Open-source components registered in THIRD-PARTY-COMPONENT-REGISTER may be used behind a LUMENIS adapter; each screen's operation flow follows LUMENIS specifications and does not copy another product's flow.

## 34. Ordered cross-surface delivery and acceptance

This section retains the approved fifteen-checkpoint dependency coverage in `LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md`. Dispatch is C1–C6 under AGENTS.md, with independent frontend F throughout; retained ROUND 08/09–14/15 requirements cover foundations, workflows and final integration, not another execution sequence. Do not implement a future surface or provider before its owner, contract and entry gate are approved.

Do not build all screens from a generic template. Work in this order, with a capability-parity gate between phases:

1. **Bind truth:** classify each Experience screen/action by owner, endpoint, ViewModel fields, permission, Evidence, read/write effect and known gaps. Resolve unknown owners from source before creating a new API.
2. **Make the shell real:** implement Product Core connectivity, current context, routing, error/offline/retry states, keyboard/focus behavior and restorable navigation. The optional LUMENIS account is part of current engineering closure and must not block ordinary browsing or existing product use. Keep server Permission/effect fences intact, and keep media Cookie/session authorization entirely inside the SYSTEM collector/browser chain. Keep CTH SubjectContext separate from BMP BrandFocus.
3. **Prove the five Golden Pages:** AI-01, CTH-01, BMP-01, SH-01 and SYS-01 each use their semantic signature in §25 and bind to live owners. Do not mark a fixture-backed page complete.
4. **Migrate by workflow family:** bind remaining contract screens only after their source/API/Permission/Evidence owner is verified. Preserve established behavior before removing any migrated surface.
5. **Reach surface parity with independent evidence:** build and verify Public Website, Web Workspace, Windows/macOS Desktop and iOS Mobile in parallel under their approved roles. Each receives its applicable interaction, accessibility, viewport/device, error/recovery and visual checks at §20 widths; do not make one surface's closure a prerequisite for another. Verify Public Website acquisition/workspace-entry separately; do not require identical layouts.
6. **Release evidence:** require applicable compilation, static quality/security/data checks, actual complete user runtime/E2E, clean-clone build/runtime acceptance and current-main CI evidence. Follow the current root AGENTS.md and machine contract: targeted unit/integration regressions may be used for a relevant defect, but are not a blanket requirement and do not replace real user outcomes. Preserve historical files and failures. Record unavailable infrastructure as `UNVERIFIED`, never as PASS.

For each domain, acceptance must include its invariant in §30, real ViewModel truth, permission response, Evidence trace and return, honest missing/error states, keyboard/touch operation, reduced motion, persistence or explicit non-persistence, and the result after a real action. A screen is complete only when its user task completes end to end.

## 35. Product module map and end-to-end delivery standard

The 44 screen IDs and 54 binding records (`BACKEND-GAP-001..054`) are the existing coverage baseline, not a limit on page count, content families or approved capability scope; all approved outcomes still require design and verification. The machine-readable binding registry constrains only data/API/actor/permission/evidence truth; it is not a layout system. Legacy `sectionTypes`, card lists and generic ViewModel shapes are inventory clues only. They must not dictate layout, flow or component placement. No shared renderer may turn these 44 IDs into one template with substituted titles and fields. Every screen below has a distinct question, visual composition and primary interaction. Existing ledgers may be used as evidence inputs, but their owner/status labels do not override current source or establish that an API exists. Any conflict stays visible as `CONFLICT` until source inspection resolves it. `UNKNOWN` is an explicit delivery gap.

### Product capability map

| Capability family | Product owner and scope | Required product outcome | Truth boundary |
| --- | --- | --- | --- |
| Runtime and work context | SYSTEM runtime/permission and the optional product account under the existing account owner | Open the pre-beta product without an account wall, restore safe local work context, and expose a truthful local restriction only where a protected operation requires it | UI context is not proof of authorization; every protected server operation still enforces Permission/effect boundaries; media platform Cookie/session state is separate |
| Commercial operations and subject intelligence | CTH | Start in authorized GLOBAL_ALL commercial intelligence, optionally narrow to a Subject; read commercial signals, event stream, cases, risk, decisions, actions, schedules and reports; resolve the exact target when an operation needs it and trace each decision to source and follow-up outcome | Subject ownership, CTH metrics and confirmed outcomes remain CTH-owned |
| Brand and market intelligence | BMP | Start in authorized GLOBAL_ALL brand/market intelligence, optionally narrow to BrandFocus/Market; connect category movement, competitors, audience, creators, content, channels, campaigns, brand risk and evaluation | Brand focus and BMP metrics remain BMP-owned; competitor and creator data are relationships, not interchangeable subjects |
| Analytics and decision support | Shared analytical capability with CTH/BMP-owned metric definitions | Cohort, compare, segment, trend, attribute, detect anomaly, explain change and export an auditable view | Shared computation keeps source domain, definition/version, scope, window, freshness, confidence and lineage; it cannot relabel a metric or combine incompatible scopes silently |
| Business operations | CTH for commercial cases/actions; BMP for brand campaigns/marketing workflows | Convert a signal into an owned decision, accountable task, due date, status, approval and measurable follow-up | Each action is written by its source-domain owner; Shared provides orchestration/trace, not a replacement workflow truth |
| Brand marketing and growth | BMP | Plan positioning, audience, campaign, creator/channel mix, content variants, launch calendar, budget/goal and evaluation | Proposed, approved, scheduled, published and measured are separate states; no simulated metric is presented as actual reach or ROI |
| Media creation and propagation | Independently usable Shared creation; BMP/CTH owns business intent only when its task is explicitly linked | Directly create/edit/version/export documents, video or podcasts; optionally adopt permitted research/domain assets and return to that linked task; publication retains separate authorization | Project/workspace rights and actual source lineage persist; no forced business task or invented Subject/BrandFocus; a queued/published adapter result is not proof of business impact |
| Media platforms and connectors | SYSTEM integration adapters; product context remains CTH/BMP | Inspect existing Cookie/session connector health, quota, capability, schema mapping, sync status and recoverable errors; use the current authorized operational import/replacement path when recovery is needed | No new platform account/login flow is inferred; connector state is operational truth only; platform metrics retain source/time/definition and map into the originating product scope |
| AI and Agent Groups | Existing shared enhancement within the actual calling CTH/BMP/Shared/SYSTEM task and permissions | Research, draft, explain or assist permitted product actions with relevant sources and reviewable trace; support independent creation without inventing a business context | Model output is derived content, not Canonical fact or authority; absent inference never blocks normal manual/deterministic work |
| Evidence, evaluation, learning and reporting | Shared Capability | Preserve the evidence chain; evaluate source-backed outcomes; learn from reviewed feedback; produce reproducible reports/exports | Preserve `originDomain`, source IDs, actor, timestamp, policy/model/version and transformation lineage |
| Runtime, security, collection and recovery | SYSTEM | Show health, collection/platform state, permissions, configuration, audit, backups and recovery actions | SYSTEM is infrastructure truth only; it must not acquire CTH/BMP business objects or metrics |

### Required interaction patterns by form factor

- **Web Workspace:** primary browser entry for real workflows; optimize for URL/deep-link restoration, keyboard/pointer work and responsive evidence inspection over the same canonical contracts.
- **Desktop:** optimize for dense, multi-source decisions and approved local capability: context remains pinned; comparisons can be viewed side by side; timelines, tables and graph relationships support keyboard sorting/filtering; an inspector exposes lineage without obscuring the task; bulk actions preview impact and require the owning product's authorization.
- **Mobile Companion:** optimize for timely review and a single owned action: keep Subject or Brand focus visible; provide a compact signal feed, prioritized alerts and a one-task action sheet; allow capture/review/approval and source trace; restore the exact originating campaign, case, filters and scroll position on Return. Dense analysis can be summarized, but its definition, uncertainty and source remain inspectable.
- **Public Website:** optimize product comprehension, credible capability demonstration and low-friction trial/contact/workspace entry. It never presents marketing fixtures as live production results.
- **Shared UI:** loading, no data, not collected, stale, blocked, permission denied, offline, partial result and failure have distinct copy and recovery actions. Charts, AI summaries and status badges always disclose the selected scope and time window.
- **Signature behavior:** Trace / Return follows a signal or creative through source → interpretation → decision → authorized action → observed result, then returns to the same working context. This causal continuity, coupled with the Point → Axis → Trace → Field → Strata → Boundary spatial grammar, is the LUMENIS-owned interaction signature. Visual novelty must follow this workflow and must never disguise missing data or authorization.

### Executable design and accessibility thresholds

- **Tokens:** define semantic foreground/background/status colors, type roles, spacing, density, focus, elevation and motion as named tokens before composing screens. Color expresses meaning and never carries status alone. Text and interactive states meet WCAG 2.2 AA contrast; standard text contrast is at least 4.5:1, large text at least 3:1, and keyboard focus is visible against adjacent colors.
- **Input and size:** interactive touch targets are at least 44 × 44 logical px where the platform permits. Keyboard-only users can reach, operate and leave each control in logical order; pointer, touch and keyboard actions produce the same authorized business result.
- **Text and localization:** the observed shell may support fewer locales than the three-language product commitment; that is an implementation gap, not permission to drop Korean. Before claiming a promised screen or surface accepted, verify `zh-CN`, `en` and `ko` copy from the canonical registry, locale switching/persistence and Return, all business/error/permission states, short/long translations, mixed CJK/Latin numerals, wrapping, font scaling to 200%, right-sized desktop windows and screen reader names. Never bake translated labels into metric/API identifiers or treat a fallback string as a completed translation.
- **Responsive navigation:** desktop uses a persistent or collapsible domain rail plus restored work context; tablet uses a compact rail and reversible detail panel; phone uses one primary task surface with a clear back path. Test portrait and landscape, desktop narrow-window transitions, keyboard shortcuts and hardware back. Return restores selected Subject/Brand, filters, tab, selection, scroll and originating route.
- **Motion:** establish named duration/easing tokens and use motion only where it explains causality, progress or a reversible transition. Every transition is interruptible and has a reduced-motion path; reduced motion removes spatial travel/parallax and keeps state-change feedback immediate. Motion must not be the only status signal.
- **Performance:** target 60 fps on supported reference devices and keep p95 frame work within 16.7 ms during defined Golden Page interactions. Defer non-visible work, virtualize long lists and provide a no-motion/low-cost rendering fallback on constrained devices. Record the reference device, build mode and measured interaction; a simulator screenshot is not a performance result.
- **Assistive technology:** verify WCAG 2.2 AA flows for VoiceOver/TalkBack or the target desktop screen reader, semantic headings/landmarks, chart text equivalents, dynamic status announcements, focus restoration and error recovery. A critical task must remain operable at 200% text scaling without clipping or loss of controls.

These are acceptance thresholds for implementation, not claims that the current bootstrap already meets them.

### Roles, top tasks and release scenarios

Prioritize work by real user task and authorized role, not by the size of a screen inventory:

| Role / context | Top task | End-to-end scenario to prove |
| --- | --- | --- |
| Commercial operator (CTH) | Detect a subject-level change and close the response loop | Enter authorized GLOBAL_ALL → optionally focus an authorized Subject → inspect current and historical signals → open source evidence → resolve the exact target for a case or decision → confirm authorized result → revisit measured outcome → Return to the retained context |
| Brand / growth operator (BMP) | Move from market signal to measured campaign | Select Brand/Market focus → compare category/competitor/creator signals → inspect source and freshness → plan creative/channel/campaign → obtain required approval → record delivery result → evaluate against a defined baseline → Return to the campaign |
| Analyst (CTH or BMP) | Explain a KPI change without mixing scopes | Select product-owned metric → inspect definition/window/denominator → segment or compare compatible cohorts → distinguish actual, estimated and unavailable data → export with lineage → reopen the same view |
| Media / content operator | Adapt an approved asset to an authorized platform | Open asset from owning campaign/Subject → review rights and provenance → create channel variant → preview and approve → submit through the platform adapter → inspect real adapter status/error → trace back to campaign and evidence |
| SYSTEM operator | Diagnose and safely recover an integration | Inspect connector/auth/quota/runtime health → distinguish platform outage from business-data gap → inspect audit trail → request permission/approval where required → apply bounded recovery → verify operational result without changing CTH/BMP business truth |
| Executive / reviewer | Trust a summary and inspect its basis | Open role-authorized cross-product summary → see owner, metric definition, time window and freshness → open supporting Evidence → distinguish confirmed outcome from model suggestion → return without changing source state |

Korean product-app research is a research method, not a visual dependency: record a named public flow and source, extract only the underlying principle, map it to a LUMENIS task, then test that principle with LUMENIS objects and users. No borrowed palette, signature composition, interaction sequence or source implementation becomes a LUMENIS standard.

Initial public references reviewed 2026-09-20:

| Source flow | Principle to study | LUMENIS question and boundary |
|---|---|---|
| [Toss Shopping discovery](https://toss.im/en-us/service/shopping) | Reduce search effort and connect discovery to a useful next step. | In BMP, can a market or brand insight open a low-friction, evidence-backed next step? Show source, freshness and why it is relevant; do not add opaque personalization or copy Toss's recommendation/checkout sequence. |
| [KakaoTalk Channel business home and updates](https://business.kakao.com/info/kakaotalkchannel/) | Keep business identity, updates and response paths connected to the audience relationship. | For BMP/Shared, investigate whether verified campaign/content owners can trace approved publication to real platform response and evaluation. This is a product-contract question, not a promise that publishing, chat or analytics already works; never clone Kakao's home, feed or chat composition. |
| [Toss Design System component guidance](https://developers-apps-in-toss.toss.im/landing-page/landing-page-en/design/components) | Make component purpose and usage guidance explicit for consistent implementation. | Apply the documentation discipline to LUMENIS-owned components and states only. The Toss UI Kit materials are limited to Apps in Toss; do not reuse its components, assets, tokens or visual patterns. |

The supplied [`motion-web` repository](https://github.com/Zachary-1012/motion-web) is a creative-web research reference only. Its [CC BY-NC 4.0 license](https://github.com/Zachary-1012/motion-web/blob/main/LICENSE) bars commercial integration of its Skill, prompts, cases and derivative workflows. No code, case, asset, parameter set, verification recipe or derivative workflow from it is admitted into LUMENIS; define motion and acceptance independently from verified LUMENIS state transitions and user tasks.

### Implementation sequence and release gates

1. **Freeze product semantics:** validate CTH Subject-first, BMP Brand/Market-first, Shared lineage and SYSTEM infrastructure boundaries against the current owner map. These are domain ownership semantics, not mandatory selected-Focus entry gates. Reject merging domain meanings or making Subject/Brand selection a prerequisite for a GLOBAL-capable task.
2. **Resolve all 54 bindings:** one registry row per `BACKEND-GAP-001..054`; inspect code and live contracts, assign the canonical owner, record exact callable/route and typed fields, actor/scope, permission operation, evidence fields, side effects, truth status and test. Unknown remains blocked with an explicit next action.
3. **Implement foundations:** typed API clients, session and context boundaries, deep links, cancellation/retry, offline/error handling, accessibility, event logging without sensitive content, state restoration and explicit surface capability state. Establish browser keyboard/touch and native Desktop/Mobile baselines alongside the related screen work; bind existing real APIs/Core immediately and track any missing existing-owner dependency as OPEN/UNBOUND.
4. **Deliver workflow slices:** for each capability, finish read → explain → decide → authorize → act → observe → Trace/Return before moving on. Prioritize AI-01, CTH-01, BMP-01, SH-01 and SYS-01 as distinct Golden Pages, then migrate by shared interaction/workflow family while preserving parity.
5. **Optimize analytical and operational modules:** measure decision completion time, signal-to-action time, evidence coverage, freshness, false-positive rate, campaign delivery/impact attribution quality, workflow SLA and recovery success. Each metric has a canonical definition, owner, denominator and freshness; do not optimize engagement at the cost of trust or business outcomes.
6. **Prove each surface and cross-surface continuity:** exercise Public Website, Web Workspace, Windows/macOS Desktop and iOS Companion against their real endpoints and role-specific tasks in parallel. Test pointer, keyboard, touch, screen reader, reduced motion, localization, slow/offline connection, empty/stale/partial/error states, permission denial, persistence and return where applicable. Verify Public Website entry/demo truth separately. Compare screenshots only after semantic and functional checks pass; preserve OPEN evidence where a device/runtime is unavailable.
7. **Release by evidence:** attach the binding ID and test/runtime evidence to every completed capability. A package import, generic renderer, fixture, screenshot or CI pass alone does not make a user workflow complete. Mark unavailable platform accounts, device coverage or production data as `UNVERIFIED` with an owner and follow-up.

### Definition of done per capability

```text
user problem and product owner are explicit
AND canonical definition/source and version are traceable
AND actor, scope, permission and effect are verified server-side
AND read/write path preserves domain ownership and Evidence lineage
AND success, partial, empty, stale, blocked, offline and error states are truthful
AND each approved operational surface completes its assigned part of the business task with suitable composition
AND keyboard, touch, screen reader and reduced motion have equivalent paths
AND a real action result can be inspected and returned to its origin
AND applicable build/static/security/data checks and actual user-operation/recovery acceptance pass
```

The binding registry is an implementation and acceptance ledger. It is not evidence that every planned module has shipped; completion is reported only for rows whose source, runtime behavior and acceptance are verified.

## 36. The 44 screen-specific UX blueprints

These blueprints are product design decisions, not claims that the App, endpoints, or data have shipped. The matching screen ID is retained only for navigation and contract traceability. Each composition must be built and accepted as its own workflow. A common header, typography scale, evidence citation treatment and input behavior may recur; layout grammar, primary visualization and task choreography may not be copied blindly between screens.

### Per-screen implementation and acceptance record — direct construction

The latest PO authorizes F to build directly from this Experience and existing contracts, without first delivering a design draft/Figma or waiting for M DESIGN_READY approval. Maintain the existing screen specification alongside implementation; do not create duplicate plans. Resolve the actual owner, callable and Permission before invoking dependent behavior. The record links ScreenId and binding IDs and retains:

1. Intended role, user task, entry route/context, exit paths and Trace/Return restoration behavior.
2. Key fields and their visual priority, with each field tied to its verified source/ViewModel contract; unresolved fields remain `UNKNOWN` and block implementation of dependent behavior.
3. A state matrix for loading, empty, not collected, stale, partial, offline, blocked, permission denied, error and success, with truthful copy and recovery action for each applicable state.
4. A surface matrix covering Public Website (explanation/demo only), Web Workspace (primary/available), Desktop (enhanced/exclusive) and Mobile Companion (view/notify/approve/light action), plus separate applicable layout anatomy, navigation, responsive transition, interactions, keyboard/touch behavior and screen-reader order.
5. Every read/write action's owner, actor/scope, permission decision, side effect, idempotency/reversal behavior and Evidence lineage; UI affordances are never authorization.
6. Stable test IDs and executable acceptance cases covering the real task, state/error paths, responsive behavior and Trace/Return; include widget, API/integration and runtime/E2E cases as applicable.

F records actual source, necessary layout decisions and executable acceptance in the existing `contracts/experience/screen-specifications/<SCREEN-ID>.md`. No separate pre-implementation design/M approval phase is required. DESIGN_EXPLORATION and DESIGN_READY remain design-history facts and do not auto-promote source or acceptance. An unresolved owner/API/Permission/lineage blocks its dependent operation; independent known behavior may be implemented directly. Missing runtime evidence prevents an accepted/shipped claim, not all coding. Preserve the typed contract, task-specific layout, state matrix, anti-template checks and real E2E; no shared generic renderer or substituted-title template.

| Screen | Purpose-built information composition and visual language | Primary interaction and result | PC → mobile recomposition |
| --- | --- | --- | --- |
| ACC-01 Authentication entry | Quiet, focused identity surface with one clear account form, provider choices only when actually supported, and a compact trust/status rail; no analytics shell. Auth behavior stays `UNKNOWN` until bound. | Enter credentials or select a supported sign-in method; show validation, pending, rejected and recovered states distinctly. | Centered form with help/status pane → single-column form with touch-safe fields and explicit return. |
| ACC-02 Subject and lens selection | Optional context chooser from GLOBAL_ALL: choose an authorized Subject/BrandFocus and appropriate CTH or BMP lens; identity and lens remain separate and cannot imply changing ownership. | Search/select an authorized focus or remain GLOBAL_ALL, then confirm an available lens; server response controls the destination. | Searchable split list/detail → searchable full-screen list then focused subject confirmation. |
| ACC-03 Workspace task home | Existing AI-01 task editor as the primary entry under GLOBAL_ALL or current exact Focus; compact recent work and destinations are secondary, with truthful unobtrusive runtime availability. | State a task or reopen saved work; retain the draft and selection during same-scope shell navigation. | Persistent domain rail plus task editor and compact recent-work access → task-first compact composition on small surfaces. |
| ACC-04 Access recovery and guard | A boundary/recovery screen explains which step is blocked, what scope is missing and how to recover; no fictional credentials, roles or access grant. | Retry, switch to authorized account/context, or request access through a real flow once verified. | Diagnostic steps beside the attempted destination → sequential recovery cards with clear back path. |
| CTH-01 Commercial operations overview | Scope-aware commercial operating desk: GLOBAL signals or optional Subject metrics, chronological signal ribbon, event/evidence focus and a decision/action queue. Avoid BMP's brand network composition. | Scrub a change on the timeline, inspect its source, open/create a case or decision and trace the follow-up. | Parallel metrics + timeline + action queue → one active signal with swipeable evidence and a contextual action sheet. |
| CTH-02 Subject / business-unit profile | Ownership map showing Subject → business unit → brand/format relationships, with source/owner labels and a separate context selector. | Expand a relationship and inspect its provenance; switch the selected Subject only through the authorized context control. | Hierarchical tree and relationship table → compact breadcrumb hierarchy with focused relationship cards. |
| CTH-03 Real-time monitoring | Live pulse strip with freshness clock, confirmed-vs-live distinction, source lanes and collector health band; the update rhythm is the main visual. | Pause/resume viewing, pin an event, open source evidence; health actions remain permission-gated. | Multi-source live board with filters → prioritized single stream and persistent freshness/connection badge. |
| CTH-04 Event relationships | Causal event constellation paired with a time axis; nodes encode event/case links and evidence anchors, not generic cards. | Select a node to reveal linked evidence, navigate to its case, then Trace/Return to the same graph position. | Interactive graph + synchronized timeline → vertical event path with evidence nodes and saved zoom/focus. |
| CTH-05 Sentiment calendar | Calendar heatfield where each date shows event/sentiment density with a clear scale and data-availability legend; selected date drives a linked evidence strip. | Choose a day/range to inspect events and sources; switch to list view for precise keyboard access. | Month heatmap beside date detail → week/day agenda with density marks and a slide-up evidence list. |
| CTH-06 Negative monitoring and feedback | Triage queue differentiates public opinion, customer feedback and confirmed incidents; the active item opens a source-first reading pane. | Verify original Source, classify or link to a Case, and preserve the source wording and lineage. | Dense triage table with source inspector → stacked review cards with filters and full-screen source reader. |
| CTH-07 Trend analysis | Aligned time-series canvas with metric-definition rail, comparison overlays and a decomposition panel for what changed; every axis states units/window. | Add/remove a compatible metric or cohort and inspect the contribution/evidence behind a delta. | Resizable synchronized charts and formula table → one primary chart, horizontal metric switcher and tappable delta explanation. |
| CTH-08 Case and knowledge library | Lifecycle columns for open cases and a separate verified-knowledge shelf; case timeline remains distinct from reusable lessons. | Move a case through an authorized state transition; promote a reviewed conclusion to knowledge without overwriting facts. | Board/list toggle with case timeline inspector → prioritized case inbox and step-by-step timeline. |
| CTH-09 Risk and decision board | Risk register on one axis, decisions on another, with evidence and action ownership aligned row-by-row; high-risk states are never represented by color alone. | Inspect basis, assign/record a decision, request approval and confirm the resulting action. | Risk matrix plus decision ledger → ranked risk feed with focused decision detail and explicit confirmation. |
| CTH-10 Reports and weekly brief | Report storyboard separates metric narrative, evidence citations and methodology; preview is a paged artifact with scope visible. | Select a period and verified blocks, inspect source list, preview and export with a recorded definition/window. | Outline + live page preview + evidence rail → report sections list, one-page preview and share/export sheet. |
| BMP-01 Brand and market overview | Brand-centered relationship field: brand health at center, audience/creators/channels/competitors as connected market forces; do not reuse CTH's timeline-first dashboard. | Focus a brand, inspect a relationship's evidence and jump into its market, propagation or campaign path. | Rich network canvas with linked channel and KPI strips → brand pulse summary with navigable relationship carousel and source trace. |
| BMP-02 Brand portfolio and competitors | Portfolio constellation distinguishes owned brands from competitor entities; category and identity sit around each brand, not in a CTH Subject table. | Compare or focus one brand; context switch is explicit and retains the previous focus for Return. | Multi-brand canvas and comparison columns → searchable portfolio list with focused brand profile and competitor chips. |
| BMP-03 Market intelligence | Opportunity radar plots category themes by momentum and evidence confidence, with a source brief beside the selected signal. | Filter a market/category window, inspect source provenance and mark a lead for review without calling it confirmed. | Radar/landscape with evidence dossier → ranked opportunity feed and source-reader drill-in. |
| BMP-04 Media propagation analysis | Propagation river maps channel → content → exposure → response with conversion stages and comparable time windows; no unsupported reach estimates. | Trace a campaign/content item through the funnel and inspect each platform's source, metric definition and freshness. | Flow visualization plus channel matrix → vertical funnel with channel selector and explicit metric/source details. |
| BMP-05 Creator ecosystem | Creator graph segments KOS/KOL/KOC/UGC by audience fit, authenticity, contribution and risk; transparent comparison table supports audit. | Open a creator dossier, compare verified contributions, note collaboration risk or attach to an authorized campaign. | Graph plus sortable roster and dossier → creator cards with fit/risk summary and dossier detail. |
| BMP-06 Content center | Editorial production board separates brief, draft, review, approved, scheduled and delivered assets; rights/provenance stays attached to each version. | Upload/version content, review lineage and approval, then request an authorized publish handoff. | Swimlane board with asset preview inspector → production queue with version stack and bottom approval actions. |
| BMP-07 Campaign workspace | Campaign control room arranged by objective → audience → channel mix → milestones → outcome; goals and actual results occupy separate visual tracks. | Build or revise a plan, assign owners/dates, request approval, record delivery and evaluate against its baseline. | Timeline and channel allocation side-by-side → guided milestone sequence with compact objective and status header. |
| BMP-08 Podcast studio | Audio-first editing stage: waveform and timecoded script align with research sources and speaker cues; keep this distinct from the general content studio. | Draft from an approved brief/evidence set, edit transcript against audio, review source claims and export a versioned cut. | Large waveform + script/source side panel → transcript-first editor with scrub controls and a source drawer. |
| BMP-09 Brand evaluation | Brand scorecard shows dimension, period-over-period movement, confidence and evidence coverage; narrative conclusions sit below the measured values. | Select a brand/period, inspect a dimension's definition and evidence, then compare only aligned baselines. | Score matrix with dimension trend small multiples → prioritized dimension list and one selected evidence-backed trend. |
| BMP-10 Brand risk and events | Brand incident field groups by severity, spread and recency; active event timeline leads into response ownership and evidence. | Triage an incident, assign a response, record approval/effect and revisit verified impact. | Incident map plus response timeline → urgent queue with a focused incident detail and action ladder. |
| BMP-11 Benchmark and competitor analysis | Normalized comparison workbench with metric definitions, side-by-side brand/competitor columns and an evidence strip; incomparable values are visibly withheld. | Select comparison set and time window, inspect normalization, identify a supported gap and export a traceable finding. | Multi-column benchmark grid and small multiples → swipeable comparison cards with sticky metric definitions. |
| AI-01 AI intent entry | Intent composer beside a preview of which product context and evidence will be used; suggested tasks are grounded in available capabilities. | State a task in GLOBAL_ALL or optional exact Focus, inspect authorized evidence/capability plan and start only when an executable route exists. | Composer and evidence preview in parallel → single prompt field with context chip and expandable plan preview. |
| AI-02 Capability task workbench | Task represented as cancellable stages with input/output artifacts between stages; stage transitions reveal evidence and permission requirements. | Start, pause/cancel, retry a safe stage or review a gated action before it runs. | Stage graph with artifact inspector → vertical progress path with persistent cancel and expandable evidence. |
| AI-03 Evidence-anchored analysis thread | Conversation claims are grouped by conclusion; each claim has inline evidence anchors, uncertainty labels and a provenance rail. | Open a cited source at the relevant passage, challenge/refine a claim or create an owned follow-up task. | Thread plus source inspector → claim cards with inline citations and full-screen source return. |
| AI-04 Agent and skill catalog | Capability matrix shows owner, supported task, required permissions, health and last verified call; code presence is not shown as availability. | Filter by task, inspect input/output and permission contract, then run a safe verified capability. | Matrix/catalog with capability detail panel → searchable capability list and detail sheet. |
| AI-05 AI Gateway and providers | Provider topology shows availability, latency, policy and fallback path while rules/data remain the core lane. | Inspect provider state or run a diagnostic; fallback must be observable and must not block core operations. | Gateway flow map with health table → provider status list with explicit fallback/last-check details. |
| SYS-01 Runtime health | Runtime topology traces App → API → database → adapters with current health, degradation and check time; avoid product KPI styling. | Open a failing dependency's diagnostic, inspect trace and invoke only an authorized recovery. | Dependency map with health timeline → ordered dependency list and focused diagnostic view. |
| SYS-02 Collector status | Platform lanes show scheduler, rate-limit, retry/backoff, queue and ingestion stage; failures stay outside Canonical until validated. | Inspect a run, retry/stop when allowed, and trace a collected record to its destination state. | Live operations table with per-platform drilldown → platform queue cards with persistent running/retry status. |
| SYS-03 Database and truth chain | Layered schema/version/integrity view links schema → source → canonical → evidence → metric; versions never imply readability or completeness. | Inspect a table/chain validation and open exact integrity errors; recovery is a separately authorized path. | Schema tree with chain timeline and diagnostics → chain stages with integrity summary and error detail. |
| SYS-04 Security and permission | Permission matrix maps actor × product/domain × operation/risk alongside a separate audit trail; policy and decision are inspectable. | Simulate/read an access decision, inspect policy reason, or approve only through a real second-factor/approval contract. | Matrix and audit ledger → searchable role/scope list with explicit decision detail. |
| SYS-05 Settings and appearance | Preference studio previews density, contrast, language and motion on representative CTH/BMP samples without touching business data. | Change a local/account preference, preview, save and restore defaults; announce persisted scope. | Side-by-side preference controls and live preview → grouped settings pages with immediate accessible preview. |
| SYS-06 Internal browser | Controlled evidence-capture workspace splits source page, capture metadata and audit actions; unmistakably separate from personal browsing. | Navigate only within allowed capture rules, pin a snapshot as Evidence and inspect the audit result. | Browser viewport plus evidence inspector → source capture full screen with a compact metadata/trace panel. |
| SYS-07 Evaluation and acceptance | Six-gate acceptance sequence shows owner, required evidence, result and unresolved blockers; PARTIAL/UNKNOWN remain visibly incomplete. | Open a gate's artifact, rerun a permitted check and inspect exact failing criterion. | Gate matrix with evidence detail → sequential gate cards with current blocker and artifact links. |
| SYS-08 Observability and logs | Trace waterfall links requests, runtime spans and structured errors; frontend prototype events are in a separate lane. | Filter by trace/time/component, inspect correlated logs and return to the originating runtime or task. | Waterfall and query facets with detail pane → trace summary followed by scrollable spans and errors. |
| SH-01 Content creation studio | Discover and source-to-artifact workspace: readable trends/hotspots/related works, brief and evidence rail, editable creation canvas and version/outcome lane; distinct from SH-02 library, BMP-03 interpretation, campaign planning and podcast editing. | Inspect actual works and explained relevance, carry selected locatable references into an editable real brief, review versioned revisions and hand off for human approval. | Three-zone canvas (sources/work/artifact) → focused editor with source drawer and version/action sheet. |
| SH-02 Evidence library | Search-first evidence atlas organized by source, time, domain and lineage; original snapshot and extracted citation remain adjacent. | Search/filter, compare source with extracted item, inspect freshness and open its owning CTH/BMP origin. | Dense result list with provenance inspector → searchable evidence cards with full-screen source trace. |
| SH-03 Canonical data and metrics browser | Schema/metric explorer places definition, owner, lineage and sample records in distinct panes; derived values are marked as derived. | Inspect a field or metric and traverse lineage; this is read-only exploration, not business fact editing. | Navigable schema tree plus query/result panes → table/metric list with definition and lineage drilldown. |
| SH-04 Report export center | Output queue distinguishes configuration, generated preview, completed artifact and failed export; format-specific preview appears beside provenance. | Choose PDF/Excel/PPT only when supported, set scope, inspect preview, export and retrieve audited artifact. | Export configuration and artifact preview split → guided export steps and a final downloadable artifact view. |
| SH-05 Learning and evaluation assets | Maturity shelf groups verified SOPs, retrospectives, training and evaluation sets apart from drafts; provenance and review date are visible. | Open a learning asset, inspect verification history, propose a revision or use it as a cited task input. | Asset shelves with review timeline → filtered learning library and one-asset reading view. |
| SH-06 Notifications and tasks | Action inbox separates approvals, owned tasks, alerts and informational subscriptions into urgency lanes with source context. | Triage, assign/snooze/resolve only through authorized actions; every item returns to its originating task/evidence. | Multi-lane inbox with detail inspector → prioritized queue and full-screen task action with clear origin/return. |

### Blueprint implementation rules

1. Validate each row's user problem with its intended role; amend composition where a real workflow contradicts the proposal without changing owner semantics.
2. Build each row's applicable composition over the same typed owner contract on Public Website, Web Workspace, Windows/macOS Desktop and iOS Mobile in parallel, preserving each approved role. Existing real APIs/Core bind as available; missing behavior remains OPEN/UNBOUND for its existing Owner. Public Website explains or demonstrates only verified capabilities. Do not equate responsive resizing with mobile UX or browser availability with local capability.
3. Derive screen-specific typography, data density and visualization from its task. Reuse semantic tokens and accessibility behavior, never a universal card grid, generic dashboard or template-based page builder.
4. Keep the design blueprint, binding registry and implementation state separate: the blueprint says how a verified task should work; the binding registry says where truth and authorization come from; tests/runtime evidence say whether implementation works.
5. Complete visual regression only after the corresponding real binding and action behavior pass. Review each applicable surface with its realistic long text, missing data and permission-denial states; browser viewport checks cover Web and the Public Website has its separate content/entry contract. Desktop/Mobile device evidence remains specific to those targets; acceptance on one surface never substitutes for another.
6. Treat audit/taskbook sketches, screenshots, prototypes and Figma output as reference evidence, not implementation or acceptance proof. Direct construction follows this Constitution and existing screen contracts without a design-draft prerequisite. For a generic repeated frame or unbound/fabricated behavior, M returns `REWORK`.

## 37. Scrollable editing timelines and deferred developer-mode record

### Approved shared local Read Aloud action — 2026-10-08

Provide an accessible user-triggered Read/Stop action, local voice availability
and 0.75×/1×/1.25× rate controls on authorized visible reports/Briefs and podcast
or video scripts. Preserve the existing text/scope/version owner and editing
workflow. This is script preview/review, never a replacement for final podcast
audio, video voiceover or timeline playback. Do not add speakers to every field,
create a Voice Studio, auto-play, steal focus or introduce page-level scrolling.
Expose pause/resume only when genuinely supported. Stop when the source text
version, scope or page changes; only one read-aloud session may play per surface.
Use installed local voices only, without translating text or silently changing
languages. Missing voices are clearly unavailable. Each target platform retains
its own actual runtime evidence; another platform's unit/widget result is not
acceptance. These requirements are reflected in the affected detailed screen
specifications under this same Experience authority.

The Product Owner explicitly requires a usable horizontally scrollable timeline
in BOTH video editing and podcast/audio editing. It is a necessary editing
interaction, consistent with no unnecessary page-level vertical scrolling.
Reuse the one Timeline/Artifact owner; do not create a separate audio timeline
truth. Mouse/trackpad, visible draggable horizontal scrollbar, touch/pen and
keyboard must have real reachable pan/seek paths as appropriate to the device.
Synchronize time ruler, clip/segment positions, overlays and all tracks; preserve
zoom anchor, selected clip, playhead and return context. Distinguish scrolling
the viewport, seeking playback, moving a clip and resizing the track region.
Long projects can reach both ends without clipping; dense tracks may scroll
vertically within their own necessary region. Panning alone never changes
project duration, clip positions, audio mix, source refs or saved versions.

Developer mode remains a retained historical SYSTEM capability. The Product
Owner explicitly deferred it after raising the missing entry: DEFERRED_BY_USER,
not a current implementation task or closure blocker. C6 retains the backend/
security record and F the eventual UI ownership; do not enable legacy execution
or erase its history. Resume it only under a later authorized priority change.

These requirements apply to the appropriate operational surfaces with deliberate
desktop/touch recomposition. Website explains actual available abilities; it
does not pretend to execute the local developer tools. Implementation and actual
pan/seek/reopen evidence remain separate from this rule publication.


## 38. Current frontend reference scope and scrolling

### Intelligent UI adoption — approved rules, implementation in current dispatch (2026-10-08)

The Product Owner supplied `https://x.com/i/trending/2107900056858722693` and
required research, rule adoption and a C1-C6/F mapping for later execution.
The X page returned 403 during research; the matching official release was read
at `https://openai.com/index/gpt-6-for-everyone/` (published 2026-10-07).
OpenAI describes task-shaped interactive answers and progressive rendering.
This is reference evidence; its release does not expose an installable compiler,
grant LUMENIS that capability, or change Codex/model settings.

Official scope rechecked 2026-10-09: the [Help Center](https://help.openai.com/en/articles/20001598-intelligent-ui-in-chatgpt)
limits this OpenAI feature to Chat, excluding Work, Voice and the Pro Astra
reasoning option. The [product announcement](https://openai.com/index/gpt-6-for-everyone/)
states this release does not change Work/Codex models. This does not constrain
LUMENIS's approved cross-product Experience: adopt task-appropriate presentation
and progressively useful, factual results through existing owners, not an
assumed OpenAI SDK or a change to the user's selected model. Product task/version
and save/reopen/recovery contracts remain the basis for durable UI state.

**State: research/rule adoption approved; mapped requirements remain assigned to their existing owners. This record does not establish a current window state or pause. Execution follows the latest direct PO instruction, root AGENTS and fresh local admission.**
This paragraph itself does not change dispatch or authorize a new UI engine,
product, provider or cloud dependency. Apply it within existing approved
jobs/screens after their owner passes fresh admission. This constitution remains the
sole Experience authority; research notes are supporting evidence only.

Required adaptation inside existing screen owners:

1. Choose presentation for the user's task and actual available data: direct
   text, comparison, chart, map, editable plan, form or media timeline. Keep
   plain text when it is sufficient. Do not force every result into chat cards,
   generic swapped-title pages, or a universal schema-driven screen renderer.
2. Preserve one Task/Brief, actor, domain, subject/brand focus, time range,
   budget/constraints, Evidence/citations and result version across research,
   comparison, proposal and creation. A screen transition must not require
   re-entering the same Brief or reselecting the same permitted materials.
3. AI may propose a typed presentation/interaction plan using the existing
   screen's supported components and actions. The existing Core/ViewModel,
   Permission and Effect Fence remain authoritative. Do not execute generated
   HTML/JavaScript, invented endpoints, model-authored authorization, or a
   pending action merely because it is rendered as a button.
4. Bind each actionable result to source/result version, action contract and
   applicable permission. Scope/version changes invalidate stale actions;
   failed or partial streams stay honestly partial. Show only validated pieces
   progressively, preserve focus/selection and reduced-motion preferences, and
   do not label a partial response as a saved/complete result.
5. Budget, date or source changes first produce an explicit proposed delta.
   Use existing affected-only revision, parent-version, save/reopen and rollback
   owners. Deterministic arithmetic uses actual typed units/currency/time; a
   scenario or model estimate is labeled as such, never Canonical observation.
6. Follow approved research and task contracts for overall visuals; use painted
   icons and suitable page elements without a fixed 2D/3D style. Preserve useful
   interaction, four-surface roles and no unnecessary operational page-level
   scrolling. A website explains the capability with
   truthful approved examples; Web/Desktop execute work, and Mobile exposes
   appropriate review/adjustment/approval. Do not copy ChatGPT's visual system
   or transplant its plugin-card limits into the whole LUMENIS product.

| Owner | Existing work to apply this to | Concrete handoff to F / other owners |
|---|---|---|
| C1 | Six-platform collected-result and topic/trend exploration | Typed native fields, source/time/scope/coverage, official-vs-sample heat, honest missing states, exact SourceTarget; selectable sources remain the same references downstream. No client-side invented popularity. |
| C2 | Existing AI Gateway/Agent explanation and action proposal | Grounded typed presentation/action proposals, actual model/recipe state, component/action compatibility and quality evaluation. Model output proposes; Core resolves and authorizes. No claim of UI-model training or OpenAI compiler reuse. |
| C3 | CTH/BMP comparison, decision, campaign and budget planning | Comparable units/periods/markets; editable scenario constraints; explicit revision delta and actual Action/Outcome state. Preserve the same task and sources through business use. |
| C4 | Existing pitch, video and podcast workbenches | Structured editable sections, scene/segment references, horizontal timeline, selection/edit/preview/reopen state and real media status. System Read Aloud previews authorized text; it does not become a final voice asset. |
| C5 | Research, citations, reports, SavedWork and Artifact | Click-through provenance, side-by-side source conflict/revision comparison, precise selected text, source correction impact and existing saved parent versions. No repeated import or detached display-only report. |
| C6 | Core/API/ViewModel and runtime integration | Versioned response/action contracts, bounded progressive updates, cancellation/reconnect, idempotence, stale-version/permission rejection and same-version integration evidence. No second runtime or DB. |
| F | Existing screen-specific four-surface UI/UX/AIGC | Select task-appropriate composition; integrate C1-C6 contracts; preserve context and interaction state, keyboard/screen-reader access, responsive layout and visual identity. Build directly and update the existing specification alongside code; no separate design draft or M DESIGN_READY prerequisite. |

Acceptance in each existing outcome: actual authorized material → task-shaped
interactive result → user changes a constraint/selection → correct affected
result → save/reopen with unchanged provenance → recovery and applicable
revocation. Verify normal success as well as missing data, stale result,
interrupted stream and permission denial. Compare task correctness, user
re-entry burden and time to useful result; layout novelty, animations, mock
widgets or a schema-valid model response alone do not pass. Reuse applicable
historical evidence when source and environment remain applicable. Under the
current root AGENTS.md and machine contract, targeted isolated unit/integration
regressions may be used for relevant defects; they are not a blanket requirement
and never replace genuine complete-product operations/recovery. Preserve actual
historical failures. Apply retained build/static/security/data guards and the
applicable real user E2E under the formal PO verification policy.

### 智能UI的逐步交付与组件选择合同（2026-10-08）

用户提供的论述是研究输入，官方发布来源与原始材料分别保留。以下为既有Owner内的采用要求，不包含任何窗口启停命令；实际执行以最新直接PO指令和新鲜事实为准。研究采用不代表实现完成，不宣称获得OpenAI内部编译器、权重或训练方法。

1. **选择表达，而非固定模板。** C2根据任务、现有证据、用户调整需求和设备能力提出表现计划；F以本屏已有原生组件、设计Token及动作合同承接。简短事实用文字，比较用带同口径的表/图，参数变化用可解释计算器，复杂创作保持专用编辑器/横向时间轴。用户可查看文字/数据依据并继续原任务；模型不重写导航或制造新业务动作。
2. **先给第一份有用内容。** 有可信输入时先展示已成立的事实、明确限定的比较或可读段落，再逐步补齐相关部分。空卡、骨架、重复“正在分析”和假进度不算首个有用结果。证据尚不足时显示缺口与实际进度，不先猜结论；只展示可供用户使用的解释和结果，不输出内部推理链或私密工具内容。
3. **在既有边界增量渲染。** 优先扩展现有Gateway/Task→Core/ViewModel→Flutter Screen/组件映射；所谓编译/解码只校验有类型的组件与数据提案，不新建UI平台、通用换标题渲染器、第二注册表或AI Runtime。组件类型、字段、单位、引用和动作必须由当前支持合同解析；未完成的结构片段不能作为可点击控件执行。无效块局部给出可读降级/错误，不丢其他有效内容；安全相关失败仍阻断对应动作。
4. **一个响应、可追溯的分段。** 沿原Task/run/attempt与结果版本绑定块身份、顺序/修订号、来源与数据状态；这些字段映射到现有合同或在原Owner内补齐，不建立新Truth。重复/乱序/旧run片段不重复追加、不覆盖当前版本；断线重连从服务端已确认进度继续，终止事件与连接关闭分开。只流式打印旧完整答案或播放假动画不能验收此能力。
5. **已展示内容可以纠正。** 后续来源改变结论时定位原块及依据，明确提示更正与影响；最终回答统一核对事实、数值、引用和结论，不能留下相互冲突的段落。阶段性信息标明其覆盖与未完成项，不能把局部成功标成整个Job完成。
6. **用户操作优先且不丢失。** 流入新内容不得抢焦点、强制滚动、重置选区/播放头/用户输入或覆盖已编辑块。用户改参数后绑定新的输入版本；迟到的旧计算结果失效。纯筛选和公式计算复用确定性Owner/单位与精度，不让每次拖动都重启模型或全任务；涉及保存/执行的变化仍走现有版本和Permission合同。
7. **草稿、保存、执行分清。** 分段预览可读可编辑不等于已正式保存；草稿若可恢复，必须真实有原Owner持久化回执。用户采用后通过SavedWork/Artifact或对应媒体Owner保存父版本与来源。暂停阅读、取消任务、取消外部动作分别处理；浏览器关掉不能假称任务已停止或持续执行。撤权/切换scope后旧内容及动作依当前读取权限处理，断线重试不重复效果。
8. **等待时间进入质量判断。** 同时记录请求受理、首个有用且有依据结果、首个实际可操作块、完整结果、保存成功耗时，以及事实/引用错误、修订成功、人工补救、总成本。用同任务/同材料/同预算对比原路径，兼顾p50/p95与慢设备；没有测量不承诺提速比例。不通过删内容、降准确度、偷偷换模型或开启1.5x来缩短等待。
9. **四端熟悉且连贯。** 遵循用户已批准研究及本屏视觉动线，手绘彩绘限于图标及适合页面元素；保留本屏任务结构、中英韩与可访问性，增量更新保持稳定布局，屏幕阅读器按有用段落受控播报，减少动效设置生效。必要长内容可滚动，操作端无无意义整页纵向堆叠；官网仅演示已证行为，不能执行客户私有任务。

**真实验收场景：**品牌同口径比较逐步呈现且缺值为“—”；活动预算修改后只更新受影响部分并保留人工修改；研究多来源陆续到达且矛盾被标明、更正可追溯；视频/播客参数调整保持轨道/选区/播放头并得到实际产物；中断/重连/旧run迟到/撤权/格式损坏时无重复效果。每Owner选择相关风险进行有意义验收，不全屏重复同一套测试。

**职责：**C1提供真实可得字段与时间/覆盖状态；C2在唯一Gateway内产出带来源的分段结果及受支持表现提案并评价选择质量；C3维护可比业务语义和可解释计算；C4维护真实媒体编辑与预览；C5维护引用、结果分段与版本保存/更正；C6承接既有Task/API的顺序、流式传输、取消和恢复；F实现本屏组件、稳定增量布局、直接编辑与四端无障碍。C2/C6修复AI-01真实提交与Gateway执行路径的后端断点，同时F完成该屏完整界面、其他模块继续独立建设；仅依赖该后端动作的验收保持OPEN，不阻塞整屏、其他能力或确定性路径。

C2后续可将经准入的“任务→表现选择→操作结果→评价”作为已有学习流程的样例。采用UI规则不自动授权第三方内容训练，不以模型训练完成替代产品运行。


### 全产品智能交互执行细则 — Product Owner 2026-10-08 增补

当前已绑定动作限定本轮可执行范围，不限定已批准的产品终态。任何尚未接通的既有能力必须列为现有 Owner 的 OPEN 依赖，补齐合同、真实正常结果与恢复验收；不得因接口暂缺把完整交互目标缩减成只读页，也不得用未绑定按钮假装已实现。

适用范围是全部现有能力与四个入口：44个App屏幕、官网已有内容家族，以及贯穿其中的导航、检索、列表、详情、编辑、设置、通知、导入导出、任务接续、错误与恢复。不能只在首页、AI聊天或少数展示卡片采用。该要求改进现有能力的呈现和操作，不新增业务、页面家族或第二渲染系统。

**每个现有屏幕规范必须明确以下八项，并在本屏真实用户任务中验收：**

1. **用户任务与最合适的表达。** 写清这屏要让用户理解或完成的事情，以及表格、图、时间线、对照、表单、阅读器、画布或直接文字的选择理由。简单信息保留简单表达；复杂编辑给足操作空间。解释图先按真实关系选择流程、比较、结构或时序，同一图保持清楚的主要阅读顺序；静态内容完整，必要交互帮助理解真实结果。开源等距图解/图表方法可二次适配现有组件，但不指定全局二维/三维风格、不复制供应商界面、不增加图表运行系统。不能把“每个角落”解释成处处自动生成或处处加聊天框。
2. **可理解的真实数据。** 每个事实可追踪原来源、主体/城市、出版/发生/采集时点、样本范围、单位/币种与版本。平台热度、内部样本计算、模型估计分别标明；缺失、零、未采集、过期与不可访问不混合。图表筛选不会偷偷改变统计口径。图形、标签、说明、可访问文本与导出共享同一已核验结果/版本，禁止手工重填数值造成漂移；图示的几何与连接关系需有数据依据，不以精美结构暗示未经证实的因果。检查三语长标签、遮挡/裁切、连线归属、窄屏、缩放和静态导出。原有动效完整保留，用户可跳过或选择减少动态；跳过不丢结果或操作。
3. **用户可以直接操作。** 用户能选择、对比、筛选、调整参数、检查引用、局部编辑或启动本屏已有动作。按当前功能确定实际控件，不以装饰动画代替操作；结果和操作就近出现，有明确的返回、撤销和后续工作入口。
4. **同一任务连续使用。** 将当前Task/Brief、actor、GLOBAL/Focus、材料选择、时间/预算约束、Evidence、版本、选区/播放头随当前合同传递。研究→方案→文稿/视频/播客不重复输入。跨端重开恢复到该任务允许的状态；不得仅携带页面标题而丢失业务上下文。
5. **变化可解释、可采用。** 调整预算、时间、来源或作品局部后，显示影响范围和建议差异；用户明确采用后由原Owner保存新版本、父版本与原因。未受影响内容保持；旧成果可重开/回滚。预测场景不覆盖真实观测，来源更正不改原Evidence。
6. **执行真实且可恢复。** 可交互项绑定现有服务动作、版本与Permission。加载/部分/无记录/未知/离线/拒绝/失败/取消/重试有本屏含义；可安全恢复同一任务，不重复外部效果。只有Core确认的保存/执行回执才能显示成功。AI不可用时保留仍可工作的确定性阅读、筛选、编辑与保存，不假装AI已执行。
7. **四端与无障碍。** 官网解释和演示须对应实证状态；Web/Desktop承载完整工作；Mobile按已有职责重排查看、审阅、调整和接续，不缩小PC画面。键盘、触控、屏幕阅读器、焦点、缩放和减少动效均可用；保留中英韩。操作端无必要的整页上下滚动，必要长文/表格/无障碍区域仍能滚动，视频与播客有实际横向时间轴。
8. **序境自己的视觉。** 五位架构身份与功能对象可用原创手绘彩绘图标；部分适合的页面元素也可用彩绘。整体视觉空间、层级、布局、动效和交互依用户已批准研究、当前任务及本屏合同，不限定二维，也不预设全三维。功能glyph清晰，身份图标、功能图标和第三方来源icon分层；颜色丰富但有语义节制，图像不表示数据或权限状态。人物按当前脚本描述创造，不复制参考照片人物。不复制ChatGPT、社交平台或通用SaaS模板。外来方法、组件、工具及采集/导入内容的产品外壳、阅读视图、反馈、结果与编辑器遵循适用研究和任务合同，不直接暴露供应商控制台或开发诊断。保留原文、署名、真实封面/媒体和原始网页；内置浏览器的来源页面不是可为统一风格改写的证据。

**真实世界验收至少覆盖：**不同城市同名主体、不同期间/币种不可直接比较、来源撤回、预算变更、长任务中断、权限收回、模型不可用、资料不足及跨端继续。每个屏幕挑其实际相关风险，不在不相关页面硬加控件或重复全部测试。验收同时证明正常成功路径：有用结果→用户调整→正确局部结果→保存→重开/恢复；仅能拒绝错误输入仍不交付。

**统一交付记录：**每个屏幕在自己的既有规范中记录任务、对应Source/Core输入与动作、四端差异、视觉动线、上述验收证据和未闭项；44屏索引统一放在 `contracts/experience/screen-specifications/README.md`。既有文字视觉草图保留历史，并以日期标明本次任务动线增补；不建立另一份执行蓝图或复制另一套UI引擎。蓝图、Experience、Owner、屏幕规范、草图与README同批发布，按同一提交核对；历史草图不是已实现视觉资产，也不能自动获得DESIGN_READY。

**实现准入：**最新PO允许依既有Experience/ScreenSpec与真实合同直接构建，不以独立设计稿、Figma或M逐屏DESIGN_READY审批作为编码前置。必要设计决定和证据随代码回写原规范。未知Owner/callable/Permission/lineage仍阻塞其依赖行为；真实完成、质量与用户验收标准不变。授权状态服从最新直接PO与实际依赖，不从历史设计流程推导停工。

Research evidence and exact source/owner mapping:
`evidence/round-15/INTELLIGENT-UI-ADOPTION-20261008.md`.

The actual F user turns are retained in USER-ADDITIONS-20261004.md; their latest
instruction supersedes prior exhaustive historical-video execution obligations.
The Product Owner's 2026-10-04 resume is historical scheduling evidence, not a current start command. F follows the newest direct PO dispatch and fresh local admission; the 2026-10-08 receipt is dated history. The two new
recordings d16fc1c8ad774b0e950e3e7a4e444fe3.mp4 and
7ac450632cf2611ee2ff3a6b29a41669.mp4 plus the earlier five, valid existing
analysis, OpenAI official pages and current product rules are the current study
inputs after explicit resume. Preserve all old originals/analysis, not another
historical-video reading gate. No current rule update itself analyzes frames.

### Five architecture role identities — current visual map (2026-10-06)

The five recurring architecture roles use distinct original painted identity
icons. This map defines icon identity only. It does not add product
domains, Agents, services, model providers, user-selectable roles or
authentication/Permission roles.

| Architecture identity (zh-CN / en / ko-KR) | Existing screen families | When the identity may appear |
|---|---|---|
| **CTH 商业运营 / CTH · Commerce operations / CTH · 상업 운영** | CTH-01–10 | In a real commercial-operations task or when clarifying a CTH business object; never as a substitute for a mall, tenant brand or platform identity. |
| **BMP 品牌市场 / BMP · Brand and market / BMP · 브랜드 및 시장** | BMP-01–11 | In a real brand, market, creator, content or campaign task; identity and meaning come from the actual brand/Brief. |
| **Shared Capability 共享能力 / Shared · Shared capability / Shared · 공유 기능** | SH-01–06 and cross-domain result handoffs | When making the existing source-to-result shared workflow legible; it never stands in for a Source or Evidence fact. |
| **System 系统 / System · System / System · 시스템** | SYS-01–08 | Only when explaining a real service state, security/runtime condition or recovery path; it is not the default user-navigation persona. |
| **序境自研AI / LUMENIS-owned AI / LUMENIS 자체 AI** | AI-01–05 | Only for a real AI task, source explanation, result or unavailable state, through the existing single AI Gateway; suggestions remain inspectable, editable and rejectable. |

Agent is an execution/coordination pattern inside the existing Agent Runtime,
not a sixth role identity. The owned-AI identity adds no Gateway, model service,
autonomous permission or product domain. Users do not choose these identities
for login, account, access or action authority.

The five painted identity icons use distinct task-relevant silhouettes and
controlled accent colors; this icon treatment does not define the product-wide
visual style. Functional controls continue to use clear linear glyphs. The five role
identities, third-party source marks and functional glyphs remain separate
layers. Color, pose or illustration must never imply connection, success,
failure, permission, popularity, confidence or factual truth. Source/market/work
objects may use task-specific illustrations, but do not create extra recurring
role personalities. Characters in AIGC follow the user's script/description.

The previous generic Agent/object-family role description in the historical
`work/frontend-2026-10-03/LUMENIS-ICON-REVISION.md` no longer defines the number
or allocation of current role identities; retain that file as historical icon
research, not as a competing authority. During the approved four-surface
frontend work, map existing Website, Web Workspace, Desktop and Mobile role
artwork/icon versions to these five identities, retain source/version/hash and
mark unmapped material as historical or pending replacement. This rule does not
create or replace art assets or accept a screen.

Linear icons and original colored icons coexist. Choose whether to show one of
the five architecture identities by the real task, with readable labels and
accessible contrast; do not reduce the product to monochrome or indiscriminately
color every control. Rich but controlled color remains permitted.

Apply the recorded launch/re-entry and Manus work/operation ideas through this
sole Constitution for Public Website, Web Workspace, Desktop and Mobile. Study
visual AND functional presentation, composition, UI/UX/AIGC and task-specific
useful interaction. Define UI/AIGC balance by screen/task/purpose, not a generic
percentage or replacement of factual controls. Keep the existing approved
original LUMENIS mark consistent across App, Website, favicon and native/package
uses under §23; reuse the existing mark and do not design a replacement here.
Keep functional line glyphs, the five painted identity icons and third-party
source marks distinct under this section. Startup/re-entry and task progress
must show the actual approved state, next action and useful result; user-facing
AIGC effects must serve the current task/Brief and real supported capability,
with inspect/edit/accept/reject paths where applicable, never decorative
placeholders or claims of work not performed. The Website has
text, interaction and original creative operation videos showing actual intended
workflows with accurate build/capability status. Recording references are
principles, not authority to copy proprietary assets or claim an unimplemented
operation is live. A front-end showcase does not prove a real business result.

Operational surfaces except Public Website do not require unnecessary page-level
vertical scrolling. Keep primary work/actions usable in the viewport through
task-specific panes, reversible disclosures/navigation and editing canvases;
necessary long-document/table/detail/accessibility regions may scroll without
clipping, losing context or flattening all screens into the same template.
Website may scroll according to its content. Actual video AND podcast timelines
retain required horizontal pan/seek, ruler/track synchronization and accessible
device controls. Public Website, Web Workspace, Desktop and Mobile keep their
approved roles and full capabilities rather than becoming scaled copies.

C1 supplies source-backed text/image presentation examples in the approved
LUMENIS style: retained platform-native fields, exact entity/city/venue/time,
Evidence/citations, question relevance, readable result, uncertainty and versions.
Genuine source images use their permitted rights; rendered/style illustrations
are explicitly labeled references, never substituted for source photographs.
Examples must not recreate RedNote/Douyin/X/etc. feeds. They stay evidence/design
exploration until the current F screen-specific DESIGN_READY owner accepts
the real composition; C1 does not become a second frontend/design authority.


### Consolidated four-surface reference mapping — 2026-10-04

Cue Website is the main visual, page-rhythm and interaction-presentation reference
for Public Website only. Web Workspace, Desktop and Mobile retain the established
product rules, task-specific composition, creative workbench and AI/Evidence/
Permission/Recovery contracts, adapting suitable Cue principles without scaling
the Website. The same five architecture identities above map across all four
surfaces; Agent does not add another identity. This scope follows the human messages
`01a1057b-200e-7a01-b256-cf1faabb2c9b` and
`01a10576-48c2-7e53-abe6-e445d94f2b68`, reconciled by M on 2026-10-04.
The 319b creative video applies
only to Public Website. d16fc is Cue Website operation narrative; 7ac450 is the
startup/authorization/onboarding state machine. Retain the earlier five videos,
existing analysis, Manus 2.0 and OpenAI official materials as supporting inputs.

The local report `work/frontend-2026-10-03/FRONTEND-REFERENCE-EXECUTABLE-20261004.md`
sections 12/13 supplies evidence, not design authority. Its earlier 34,245-byte
snapshot SHA256 `6b662e3798cec98a372bb36a8b9f9614c3adb10bbeaa6b5dbce4382c4cf6ca32`
and W6 review are superseded evidence. F corrected the 319b claim: the old report
had read only sheets 1 and 11–30; 4,484 extracted frames / 150 sheets do not
establish full visual or semantic reading. The old 7ac event time ranges also
require correction. Record
extracted, actually read and unresolved intervals separately; require a new
source-pinned reading receipt before claiming complete analysis. Independent
implementation with sufficient current design evidence continues.

Preserve functional line glyphs, the five original painted architecture
identity icons above and third-party source icons as three distinct layers.
Content/object illustrations remain local to real task and content identity;
they do not create another recurring persona or signal truth/state/authority.
The old fixed AIGC percentage quota was added by
the assistant without a human or measurement basis and is withdrawn. Determine
visual/proposal emphasis from the actual task and its approved screen contract.
Keep painted icon treatment and Brief-driven character choices within
the existing Experience owner. Manus/OpenAI informs architecture principles,
without adding another runtime, provider, editor, account wall or design system.

F1–F5 are prioritized work-package examples, not a scope boundary; F's full scope is the existing Owner card and all approved capabilities/screen/website requirements, including: entry/startup (ACC-03/Launch/AI-01), accessible
visual primitives, AI-01 and content reading, SH-01 video plus Shared audio,
and Public Website operation narrative. C4 owns media behavior; C3/C5 supplies
task/material contracts; C2 supplies actual AI state; W6 binds API/runtime/
Artifact and publishes accepted results. GLOBAL/ALL, artifact-first AI,
same-source use permissions, reversible drawers/Trace/Return, horizontal media
timelines, locale/accessibility and failure/recovery remain required.

Website requires text, controlled interaction and honestly labeled operation
video/demo with pause/skip/reduced-motion/failure fallback and an actual entry.
Operational surfaces retain task-specific panes and necessary long-content
scrolling without unnecessary full-page scroll. Classify reference conclusions
as OBSERVED / INFERRED / ADAPTED / DEFERRED / UNAVAILABLE. Record implementation,
tests, live operation and acceptance independently; a research report, demo,
frame extraction, gate or build cannot establish Product Truth.

Apply the existing Nielsen ten-usability-heuristic research to every applicable
user operation through the existing screen/task contracts: show actual system
status and use the user's business language; preserve user control, undo/cancel,
return and revocation; keep behavior consistent; prevent avoidable errors; make
choices and current state recognizable; support efficient paths for repeated or
expert work; keep presentation focused; explain and recover from real errors;
and provide help in the context where it is needed. Map each applicable principle
to the concrete action, state, owner, source/API path and real acceptance evidence;
do not mark a whole product passed by citing the heuristic. Preserve the existing
research and user materials, including `work/frontend-2026-10-03/NIELSEN-OPERATION-MAPPING.md`,
`work/frontend-2026-10-03/textbook-research/教材到序境-开发采用说明.md`, Apple HIG,
W3C/WCAG, and approved user videos, hand drawings, Logo/icon and Intelligent UI
inputs. Their presence is not proof of complete reading or adoption; use existing
material manifests and record unread, missing, unadopted or unverified ranges
honestly. Domain-specific industry, media, math, REA and AI materials map to their
existing domain rules and owners, not F alone. This is an adoption path within
the sole Experience and existing owner records, not a new authority or inventory.

Latest direct PO clarification: ordinary product flows present useful analyzed
results and business actions, not math/model reasoning workbenches. Remove internal
algorithm/paper selectors, arbitrary mathematical parameters and developer task
diagnostics from normal CTH/BMP/research/creation/settings/browser operation. Users
may edit genuine objectives, time, budget and other business constraints, inspect
source/coverage/uncertainty, and save/revise/reopen results. The backend selects and
executes applicable methods. AI chat alone may render user-facing analysis
explanations, useful progress and evidence-backed rationale; private internal
chain-of-thought is not a product view. This applies to all corresponding surfaces,
not only one currently visible page. Verify actual loaded assets and routes after
repair: changed source without rebuilding/loading the served application is not
evidence that the old controls disappeared for users.

REA research may inspect corresponding permitted websites/apps/upstream projects
for current functions, including acquisition gaps; the named examples are not a
ceiling. Reuse previous research and the existing REA, map actual task/state/input/
output/recovery behavior, then adapt it into original LUMENIS presentation through
the current owner. External page structure or inferred behavior is not source
truth, a license to copy restricted assets, or new product/OS-control scope.


### 真实用户期待与操作采用 — 2026-10-12 PO 增补

核实身份：ChatGPT 的 GPT-6 Intelligent UI、Meta Muse 产品（Muse Spark 为模型）、
Manus Cue、xAI Grok Bot（区别于普通 Grok 聊天）。以下公开资料于 2026-10-12
查阅；官方能力、个人反馈/媒体体验与序境设计判断分别记录。少量样本不代表
全体用户；官网声明不证明可靠性。缺反馈时继续补查官网、帮助、演示、更新和
可信评测并解决适配问题，不留空搁置，也不编造共识。

| 对应产品与证据 | 有用操作和反面信号 | 现有序境 Owner 的采用/修复 | 实际验收出口 |
| --- | --- | --- | --- |
| ChatGPT：[官方 UI](https://openai.com/index/gpt-6-for-everyone/)；[用户讨论](https://www.reddit.com/r/OpenAI/comments/1x045qs/gpt6_and_intelligent_ui_for_everyone/)中有图表/交互学习好评，也有跨端可用性和模型命名困惑 | 按任务选择文字、表格或图示，交互帮助理解和操作；不要求理解模型名才能使用 | C3/C5 后端给已分析报告，C4 给制作结果，F 按任务组织内容；C2/C6 提供实际增强和运行状态；保留文本、复制、导出和无障碍 | 图文数值/来源一致；修改真实预算/时间只更新相关内容；保存重开同一版本，各端单独实操 |
| Meta Muse：[官方说明](https://about.fb.com/news/2026/09/introducing-muse-personal-ai-agent/)描述可审阅执行和撤销授权；[一周体验](https://www.androidauthority.com/meta-muse-one-week-later-hands-on-3718233/)认为引导上手、补充条件有用，初始搜索仍需改进 | 从目标/范围/约束开始，结果可补条件；不能靠隐含记忆扩大访问或虚报连接 | C3/C4/C5 保留独立任务和局部修订；C2 采用有范围可检查上下文，C1/C6 保持原权限/来源/调度；F 呈现所用资料和重要变化 | 新旧结果可比较和重开；撤回来源后不能继续引用；断线不丢编辑，重连先读回而非重复执行 |
| Cue：[Cue 官网](https://www.cue.im/)（Manus 通用 Agent 文档不单独证明 Cue 专属能力）；[新用户不知如何开始](https://www.reddit.com/r/ManusOfficial/comments/1wx9yy5/i_dont_know_how_to_utilize_cue_what_is_the/)及[早期用户期待](https://www.reddit.com/r/ManusOfficial/comments/1x2txme/cue_agents_by_manus_a_lot_of_potential/) | 内部角色协作有用，但用户应知道输入与成果，不能承担代理配置负担 | F 以 CTH/BMP、研究、提案/视频/播客任务命名入口；C3/C4/C5 独立能力可选联动，C6 保持同一任务/版本身份 | 无内部 ID 或模型选择也可新建/续接；独立制作不强迫建 Case；跨任务不丢编辑。Cue 官网视觉节奏仅用于 Public Website，不套到工作区 |
| Grok Bot：[官方概览](https://docs.x.ai/grok-bot/overview)、[例行任务](https://docs.x.ai/grok-bot/skills-routines-and-automations)；[单用户报告部分完成却被告知全部成功](https://www.reddit.com/r/GrokBot/comments/1x25119/grok_bot_computer_lagging/) | 查看、停止、续做要有效；执行、提交、读回和目标完成分开，不信任模型口头报成功 | C1 逐来源留结果，C2 消费 Owner 回执，C3/C4/C5 核验真实业务/文件，C6 负责持久化/幂等，F 如实显示部分成功 | 成功分子/分母与真实成果一致；超时先核已提交结果，仅重试安全失败项；可取消/读回/修改；不恢复通用电脑控制 |

同一聊天入口可在任务执行期间继续输入，独立需求归入可辨认的任务，补充/修改/停止明确作用于对应任务，不能因异步顺序改变而串线。默认简明确认真实接收，随后交付有用成果、来源/限制和下一步；长期任务可查看真实状态、停止与续做，不展示私有思维链，也不把“后台工作”画成假进度。已有任务/历史按需展开，不能强制用户为每个需求另建会话，也不能取消项目和独立制作入口。

后台完成消息与内部执行摘要走不同投递语义：复用现有通知/结果Owner，只对有用完成、重要异常或必要决定打扰；去重与断线补送不能重复业务效果。用户主动询问有答复，必要审批有确定控件且不能被静默抑制；记忆可检查/更正/忘记，群体与个人可见范围不能混用。已批准Agent Groups采用同一任务与投递协议，可选@/Reply定位，不要求每个代理都回答。聊天气泡/任务卡仅服务可读性，序境视觉、Logo、角色、四端、三语、智能UI和完整独立能力保留；不得退化成纯文字IM或照搬外部客户端。

2026-10-14逐项核对：Muse设计原文保留主聊、侧聊、活动/目标视图和确定审批；Grok帮助支持并行任务及异步交接，社区个案要求状态可见、避免漏报。采用与源码缺口、商业推断校准、固定GitHub证据及组合验收统一记在 `LOOP-PLAN-20261014/product-plan-full.md` §16；本文负责呈现，规划不替代Experience权威。文档采用不证明运行完成。

表中适配是序境的设计判断，不是照抄或新增产品。复用已正确组件和服务，实际
缺口进入原 ScreenSpec/成果卡修复。Nielsen与已批准研究、原创Logo、彩绘icons及适合页面的插画/操作视频、
UI/UX/AIGC、中英韩及四端要求全部保留。增量结果不抢焦点、跳动阅读位置或覆盖
人工编辑；先给有用且范围明确的部分结果，最终核对图文/来源/状态。实现、真实
加载和用户验收分开，文档更新不升级 IMPLEMENTED/ACCEPTED。

### 完整前端与后端并行 — 2026-10-12 执行纠偏

前端的建设目标始终是完整产品可操作体验。首页直接进入现有聊天/任务界面，架构导航保留CTH、BMP及可独立使用的研究、提案、视频、播客、内置浏览器和资料/成果/设置等全部能力；不能把首页、一个编辑器、F1–F5或44规格数量当作产品全集。遵循已批准研究与任务适配的整体视觉、原创Logo、彩绘icon及适合页面的插画、实际操作视频、任务化动效/智能UI、中英韩、无障碍及四表面角色。

在原ScreenSpec/采用记录分别维护界面构造、用户交互、真实接口绑定、当前端实际验收。后台未就绪只阻塞依赖它的提交/保存/运行验收；不阻塞整页、整个模块及其他端的布局、导航、实际可用编辑/撤销/输入保留和状态构造。已存在接口立即接入；不足之处保持明确原因和继续路径，不能用演示回复/伪造数据/假保存补齐。无模型时仍有正常业务入口，不能让聊天首页变成所有业务的AI准入门。

构建工具故障修好后回到完整界面与操作建设；通过编译或一批验证后继续原完整目标。按实际用户工作纠正呈现：自然输入优先、复杂条件渐进展开；结果展示有用正文/图表/文件及来源，而非只有内部编号；成果通过可识别历史选择重开，不要求用户手输Task ID；数学方法留在后端。优先级调整不能取消尚未完成的界面、视觉或业务要求。前后端依旧分别拥有表现层与业务真相，按W6预约对接，不互写共享区域。

### 四表面并行建设与独立验收 — 2026-10-11 PO 修正

2026-10-11 直接PO修正：Public Website、Web Workspace、Windows/macOS Desktop与iOS Mobile按既有角色并行建设；Website继续使用现有`website/`，Workspace/Desktop/Mobile共用单一Flutter `app/` 和同一Product Core。直接构建任务化完整前端，不等待全部后端；已有真实API/Core立即接入，其他既有Owner依赖逐项接续，缺少的行为记录为OPEN/UNBOUND，不用模拟结果代替。保留44份ScreenSpec作为覆盖基线，不作为页面数或产品范围上限。无独立设计稿/Figma/M逐屏DESIGN_READY编码前置；设计决定随代码更新原规格。原生Desktop目标为Windows/macOS，原生Mobile为iOS；Android/Linux原生客户端不再是当前交付目标，保留历史原件和证据。Linux服务端/CI、不同操作系统的浏览器和窄屏Web不受影响。批准依据：`evidence/approvals/PO-20261011-WHOLE-PRODUCT-REUSE-EXPERIENCE.json`。

本条控制 §§23、34–36 和本节中所有“逐端实现/设计/回归/打包”的产品要求：四表面按既有角色并行建设，每个表面通过本端真实任务、运行、恢复和适用验收独立记录；一端通过不代表其他端通过或整产品Release。所有现有资料、能力与屏幕要求继续逐项映射至既有规则、Owner源码/操作及真实验收；44份ScreenSpec是基线而非上限。窗口执行依最新根AGENTS与PO直接派工，本规范不保存当前窗口停/开指令。没有接口的既有能力保持OPEN/UNBOUND并由原Owner接续；不新增产品、Owner、设计系统或付费服务。批准依据：`evidence/approvals/PO-20261011-WHOLE-PRODUCT-REUSE-EXPERIENCE.json`。

每个表面分别验收其真实入口、任务操作、结果、来源/权限、保存/修订/重开/恢复、语言与无障碍；同时遵守官网真实内容/操作视频状态及窄屏浏览器等既有要求。整体视觉依已批准研究与任务；手绘彩绘限于图标及适合页面元素，并保留可编辑设计。对已有Core/API立即真实绑定，尚未提供的接口按Owner接续并明确OPEN/UNBOUND。按Multi-Surface Decision及Real Delivery逐端记录证据；完整四表面Goal与Release要求仍按原标准核验。

### 可编辑设计工程与源码同步 — 2026-10-08 审计增补

完整范围仍为全部44屏、官网内容家族与可编辑源码；F负责前端实现，M审查成果，C1-C6保留字段/动作/状态合同职责，C6协调共享绑定。2026-10-08的F并行拓扑和其后C1-only状态都是有日期的历史快照，不是当前调度。Figma-first不再是强制前置；保留已有Figma工程/Foundation/节点与现有源码。当前执行依最新根AGENTS与直接PO指令；规范不记录实时停/开命令，不能覆盖较新的直接PO指令。免费额度、权限或调用受限时，复用现有Flutter/Dart、设计变量、SVG/矢量及本地免费工具形成可编辑设计与真实交互，不因付费工具缩减完整F范围。

在现有 ScreenSpec/README 保存 `Screen ID → 设计规格 → 可编辑载体/路径/版本 → Flutter Screen/Component → Repository/ViewModel/Action → Core/Permission → 测试/运行/Evidence` 映射。Figma 载体记录 file/node/revision；源码载体记录 Dart/Token/SVG 路径、版本及编辑/预览方法，明确不等同于原生 Figma。工具受限仅标记该路径，禁止 PNG、PPT、静态截图或伪造 .fig 冒充完整可编辑交付。复用现有文件，不重复创建，不新增收费服务。唯一 Experience、设计状态及 Product Core 真相不变。

整体升级覆盖信息架构、任务入口、导航返回、内容层级、图表/报告、资料阅读、制作编辑、浏览器、设置通知及全部状态；不能只接API、改配色或升级几个样板页。完整信息架构、组件/变量、现有屏幕与官网家族的可编辑源码和真实任务交互仍须交付，不另立设计稿阶段；不要求全部Figma页面先完成才修已有Flutter交互。各端依现有合同并行构建，已有真实Core/API立即接入，其他依赖按Owner逐项连通并记录OPEN/UNBOUND，不造模拟后端。各屏依本屏任务定义独立层级、构图和操作路径；共享可访问行为和设计变量不意味着通用重复模板。必要设计决定与验收证据同步回写原规范。ACC-03、AI-01、CTH/BMP、SH-01/BMP-08、SYS-06等既有例子帮助排序，不缩减其余能力、ScreenSpec、官网家族或新增范围。整体视觉依已批准研究与任务；手绘彩绘限于图标及适合页面元素。保留中英韩、主题、字号/宽度、无障碍和失败恢复。Figma复用可编辑组件/变量/原型，源码路径保留可编辑组件/变量/矢量与预览；提供真实载体/版本和ScreenSpec覆盖缺口。主题映射既有LumenisTheme，Website Astro/CSS共享既有语义决策；Widget通过不等于保存或跨端运行验收。

每次设计修改必须定位受影响源组件/Token/动作、必要回归和回退版本，保留未修改工作、状态恢复、焦点和路由；不得为了重构巨型 Screen/Shell 或统一样式而重写业务。CTH事件因果边、ACC-03/04绑定登记及默认入口需分别核对，缺少关系数据或真实 callable 不能靠绘图宣告完成。

验收同时看真实输入、可信 Evidence、Core/ViewModel、用户操作、成果保存/重开/修订、失败恢复和 Evaluation。SOURCE / RUNTIME / DATABASE / TEST-CI / USER OUTCOME 独立记录；设计采用、实现存在与实际完成分开。工具链升级只改善研发环境，不能算序境产品新增能力。

### 成熟操作体验与GPT / Apple / Tesla对标 — 2026-10-08

本节补充§38，不建立第二设计权威。设计先确保普通用户不懂代码也能完成原J1–J8工作：导入/选择/搜索/筛选/编辑/撤销/试听预览/保存/导出/重开/恢复，再增加来源解释、业务上下文与智能建议。AI或第三方不可用时，仍保留可独立执行的确定性操作。按钮必须有真实动作，已存在功能优先接通；未实现的原承诺保留OPEN而不降为永久只读。

| 用户与客户期待 | 本产品采用方式 | 必须看到的结果 |
| --- | --- | --- |
| GPT：输入目的后就能继续处理结果 | 按任务选文字/图/表/表单/编辑器/时间轴；建议可检查、修改、拒绝，继续原Brief和版本；保留非聊天的专业操作 | 无需重复解释或选材料；呈现和动作均有真实合同；AI建议不变成权限 |
| Apple：动作可预测、反馈清楚、能挽回误操作 | 控件/快捷键/触控语义一致；Undo/Redo说明撤回对象并展示受影响位置；进度、完成、失败各有真实反馈；普通状态内联表达，重要边界才中断 | 撤回后可见内容、项目版本和导出一致；状态不要求猜测；反馈不能谎称已保存 |
| Tesla：在当前任务里直接控制并看到状态，偏好可保存/恢复 | 复用现有任务/设置Owner保存布局/播放位置/可允许偏好，区分未保存与已保存；明确继续/停止/恢复，设备切换只恢复已授权适用状态 | 重开保留同一工作、失败不丢输入；自动状态可停止；Scope/权限不随偏好或设备转移而扩大 |

这是基于已读官方材料的序境设计适配，不宣称GPT/Apple/Tesla全站全部已研究，不复制UI/品牌资产、车辆功能或第三方登录依赖。官方读取出处及限制记于现有 `INTELLIGENT-UI-ADOPTION-20261008.md`。整体视觉依用户已批准研究和当前任务；手绘彩绘用于原创图标及适合页面元素。保留丰富而克制的色彩、按脚本创作角色、中英韩和无障碍。官网以外非必要不整页上下滚动；媒体横向时间轴和必要长内容滚动保留，不以压缩布局或减少交互损失功能。

J5/J6具体操作归既有SH-01、BMP-08规范；完整44屏与官网家族均须核对和升级，复用正确部分、定向改进真实差距，不机械全量重写或只改这两屏。实时预览、临时导出、正式保存、重开不同；Read Aloud、录音、ASR、节目成品不同；脚本变更不代表录音已改。现有组件/变量/可编辑Figma映射沿原规则，不因文档新增晋升DESIGN_READY/IMPLEMENTED。映射保留F/C1-C6完整职责；窗口状态只按最新直接PO指令和新鲜事实判断，历史恢复/等待记录不自动生效。文档更新仍不代表实现或验收完成。

客户验收采用现有Overlay两层卡：既能完成成熟基础工作，也能继续使用序境的真实来源/预算/业务范围/版本/评价。检验正确性、可修改性、误操作恢复、重复输入和有效等待，不以外观相似或控件数量判断体验达标。

### C1 媒体结果呈现 — 2026-10-09 需求澄清

依 Global §10 和已有来源/媒体/研究屏合同呈现真实媒体与理解结果，不新增独立界面或 Owner。单封面是同步采集预算，不能向用户表示完整图片或视频已分析。原帖、图位置/视频时间码、来源与派生版本可定位；原件、OCR、语音转写、视觉内容、模型解释和部分覆盖限制分开显示。排队、进行中、无权限、未取得、执行器不可用、失败和真实结果各有明确状态；无真实任务登记不显示“已排队”，无结果不补造标签/摘要。下游沿同一获准材料/Brief 和当前版本继续研究、业务或创作，不重新选择同一批来源。分析状态不覆盖原文或借界面扩大权益；本条不规定任何窗口当前开工或暂停。

### 2026-10-08 准确维度与缺失值呈现

2026-10-09 PO 无 AI 原则适用于全部已有页面与任务：沿唯一 Product Architecture 和 Real Delivery 的七域要求，始终保留真实确定性/人工操作入口、编辑、保存、导出、重开和恢复。模型不可用仅禁用对应 AI 增强并说明真实原因，不得覆盖整页为不可用、伪造 AI 结果或替用户完成判断。人工判断与 AI 建议、原始事实与派生内容分别标识。本条定义产品结果；当前窗口状态只在本地按各自直接PO指令和实际核验记录。本条不是已实现证明。

全产品原有列表、详情、比较、图表、报告及导出保留任务需要的准确维度；未取得的数值以“—”展示，并以键盘/触控/读屏均可用的说明展示未采集、来源未提供、权限受限、失败、未知、不适用或过期等真实原因。沿现有状态字段，不把所有缺值合并成0/无数据或隐藏列；CSV/API等机器输出保留null和状态，图表不画零值点或凭空补线。真实0显示0；旧观测保留其时点和过期状态。

按话题/主体/任务语义采集，再按真实出版或事件时间排序/分组/筛选，页面明确所用时间语义；采集时间单列，未知日期单列，用户显式范围保留。维度完整不等于数据采全，更不证明能力已闭环；底层Bug仍由原Owner修复。Global§10与Real Delivery共同定义证据门槛，F和C窗口按当前已批准派工实施，不重新审阅未变化的44屏材料。
